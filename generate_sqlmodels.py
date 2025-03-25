import os
import subprocess
import re
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_NAME = os.getenv("MYSQL_DATABASE")

OUTPUT_FILE = "models.py"

command = [
    "sqlacodegen",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}",
    "--outfile",
    OUTPUT_FILE
]


from sqlmodel import Field, Column
from sqlalchemy import String
import re
from typing import Dict, List, Optional, Tuple, Any

def parse_mapped_column(line: str) -> str:
    """
    Convert SQLAlchemy mapped_column syntax to SQLModel's Field syntax.
    Handles:
    - Column types (Integer, String, TINYINT(1), etc.)
    - Optional types
    - Primary keys
    - Default values
    - Different database column names
    - Foreign keys
    """
    # Try to match mapped_column style (SQLAlchemy 2.0)
    column_match = re.match(
        r'\s*(\w+):\s*Mapped\[(.*?)\]\s*=\s*mapped_column\((.+)\)',
        line,
        re.DOTALL
    )
    
    # Try to match Column style if mapped_column didn't match (SQLAlchemy 1.x)
    if not column_match:
        column_match = re.match(
            r'\s*(\w+)\s*=\s*Column\((.+)\)',
            line,
            re.DOTALL
        )
        if column_match:
            column_name = column_match.group(1)
            args_str = column_match.group(2).strip()
            # Default to str for backward compatibility
            mapped_type = "str"
            # Try to determine type from args
            type_match = re.search(r'(\w+)(\(\d+\))?,', args_str)
            if type_match:
                sa_type = type_match.group(1)
                if sa_type in ["Integer", "SmallInteger", "BigInteger"]:
                    mapped_type = "int"
                elif sa_type in ["String", "Text", "Unicode", "UnicodeText"]:
                    mapped_type = "str"
                elif sa_type == "Boolean" or sa_type.startswith("TINYINT"):
                    mapped_type = "bool"
                elif sa_type in ["DateTime", "DATETIME"]:
                    mapped_type = "datetime"
                elif sa_type == "Date":
                    mapped_type = "date"
                elif sa_type == "Time":
                    mapped_type = "time"
                elif sa_type in ["Float", "Numeric", "Decimal"]:
                    mapped_type = "float"

            # Check if nullable
            if "nullable=False" not in args_str:
                mapped_type = f"Optional[{mapped_type}]"
        else:
            return line
    else:
        column_name = column_match.group(1)
        mapped_type = column_match.group(2).strip()
        args_str = column_match.group(3).strip()

    # Parse arguments into keywords and positional args
    kwargs, positional_args = parse_column_arguments(args_str)

    # Handle column name if specified as first positional argument
    db_column_name = None
    if positional_args and (positional_args[0].startswith(("'", '"'))):
        db_column_name = positional_args[0].strip("'\"")
        positional_args.pop(0)

    # Determine column type
    sa_type = positional_args[0] if positional_args else kwargs.get('type_')
    py_type, field_args = convert_column_type(mapped_type, sa_type, kwargs)

    # Prepare field arguments
    final_field_args = []

    # Add max_length if applicable
    if field_args:
        final_field_args.extend(field_args)

    # Handle database column name if different
    if db_column_name and db_column_name != column_name:
        final_field_args.append(f"sa_column=Column('{db_column_name}', {sa_type or 'String'})")

    # Handle primary key
    if kwargs.get('primary_key', '').lower() == 'true':
        final_field_args.append("primary_key=True")

    # Handle unique constraint
    if kwargs.get('unique', '').lower() == 'true':
        final_field_args.append("unique=True")

    # Handle indexed columns
    if kwargs.get('index', '').lower() == 'true':
        final_field_args.append("index=True")

    # Handle server default
    if 'server_default' in kwargs:
        default_value = parse_default_value(kwargs['server_default'], py_type)
        if default_value is not None:
            final_field_args.append(f"default={default_value}")

    # Handle foreign keys
    if 'ForeignKey' in args_str:
        fk_match = re.search(r"ForeignKey\(['\"](.+?)['\"]", args_str)
        if fk_match:
            final_field_args.append(f"foreign_key='{fk_match.group(1)}'")

    # Build field definition
    field_args_str = ', '.join(final_field_args) if final_field_args else ''
    return f"    {column_name}: {py_type} = Field({field_args_str})"

def parse_column_arguments(args_str: str) -> Tuple[Dict[str, str], List[str]]:
    """
    Parse column arguments into keyword and positional arguments.
    Handles nested parentheses, quotes, and complex expressions.
    """
    kwargs = {}
    positional_args = []
    current_arg = []
    in_quotes = False
    quote_char = None
    paren_level = 0
    bracket_level = 0

    for char in args_str + ',':  # Add comma to force final processing
        # Handle quotes (respect escape sequences)
        if char in ('"', "'"):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif quote_char == char and (not current_arg or current_arg[-1] != '\\'):
                in_quotes = False
                quote_char = None
                
        # Only count brackets and parentheses outside quotes
        elif not in_quotes:
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
            elif char == '[':
                bracket_level += 1
            elif char == ']':
                bracket_level -= 1
            # Process argument when hitting a comma at the top level
            elif char == ',' and paren_level == 0 and bracket_level == 0:
                arg = ''.join(current_arg).strip()
                if arg:
                    if '=' in arg and not (arg.startswith('"') or arg.startswith("'")):
                        key, value = arg.split('=', 1)
                        kwargs[key.strip()] = value.strip()
                    else:
                        positional_args.append(arg)
                current_arg = []
                continue
                
        current_arg.append(char)

    return kwargs, positional_args

def convert_column_type(mapped_type: str, sa_type: Optional[str], kwargs: Dict[str, str]) -> Tuple[str, List[str]]:
    """
    Convert SQLAlchemy type to Python type and gather field arguments.
    Handles many common SQLAlchemy types and their Python equivalents.
    """
    field_args = []
    is_optional = "Optional[" in mapped_type
    base_type = mapped_type.replace("Optional[", "").replace("]", "")

    # If no SQLAlchemy type is provided, use the mapped type as is
    if not sa_type:
        return (f"Optional[{base_type}]" if is_optional else base_type, field_args)

    # Handle specific SQLAlchemy types
    # String types
    if sa_type.startswith('String') or sa_type.startswith('VARCHAR') or sa_type.startswith('CHAR'):
        base_type = "str"
        if '(' in sa_type:
            max_len = sa_type.split('(')[1].split(')')[0]
            field_args.append(f"max_length={max_len}")
    elif sa_type in ('Text', 'UnicodeText', 'TEXT'):
        base_type = "str"
        
    # Integer types
    elif sa_type in ('Integer', 'INT', 'BigInteger', 'BIGINT', 'SmallInteger', 'SMALLINT'):
        base_type = "int"
        
    # Boolean types
    elif sa_type.startswith(('TINYINT(1)', 'tinyint(1)', 'Boolean', 'BOOLEAN')):
        base_type = "bool"
        
    # Date/Time types
    elif sa_type in ('DateTime', 'DATETIME', 'TIMESTAMP'):
        base_type = "datetime"
    elif sa_type in ('Date', 'DATE'):
        base_type = "date"
    elif sa_type in ('Time', 'TIME'):
        base_type = "time"
        
    # Numeric types
    elif sa_type in ('Float', 'FLOAT', 'DOUBLE'):
        base_type = "float"
    elif sa_type in ('Numeric', 'NUMERIC', 'DECIMAL', 'Decimal'):
        base_type = "Decimal"
        
    # Binary types
    elif sa_type in ('LargeBinary', 'BLOB', 'BINARY'):
        base_type = "bytes"
        
    # JSON types
    elif sa_type in ('JSON', 'JSONB'):
        base_type = "Dict[str, Any]"
        
    # UUID type
    elif sa_type == 'UUID':
        base_type = "UUID"
        
    # Enum types
    elif sa_type.startswith('Enum'):
        base_type = "str"  # Default to str for enums

    # Add support for nullable columns
    if kwargs.get('nullable', '').lower() == 'true':
        is_optional = True

    # Handle Optional
    py_type = f"Optional[{base_type}]" if is_optional else base_type

    return py_type, field_args

def parse_default_value(default_str: str, py_type: str) -> Optional[str]:
    """
    Parse server_default value into appropriate Python literal.
    Handles various default formats including text(), functions, and literals.
    """
    # Handle text('value') format
    text_match = re.match(r"text\(['\"](.*?)['\"]\)", default_str)
    if text_match:
        value = text_match.group(1)
        if py_type == "bool" or py_type == "Optional[bool]":
            return "True" if value in ('1', 'true', 'True') else "False"
        elif "int" in py_type:
            return value
        elif "float" in py_type or "Decimal" in py_type:
            return value
        else:  # string and other types
            return f"'{value}'"
    
    # Handle func.now(), func.current_timestamp()
    if "func.now()" in default_str or "func.current_timestamp()" in default_str:
        return "datetime.utcnow"  # Return the function reference
    
    # Handle literal values without text()
    if default_str.startswith(("'", '"')):
        value = default_str.strip("'\"")
        if "str" in py_type:
            return f"'{value}'"
        elif "int" in py_type:
            try:
                int(value)
                return value
            except ValueError:
                pass
        elif "float" in py_type or "Decimal" in py_type:
            try:
                float(value)
                return value
            except ValueError:
                pass
        return f"'{value}'"
    
    # Handle numeric literals
    if default_str.isdigit():
        return default_str
    
    # Handle boolean literals
    if default_str.lower() in ("true", "false"):
        return default_str.capitalize()
    
    # For unhandled cases
    return None


def process_model_file():
    try:
        print(f"Running: {' '.join(command)}")
        subprocess.run(command, check=True)
        print("✅ Base models generated successfully!")

        with open(OUTPUT_FILE, "r") as f:
            lines = f.readlines()
            lines = [line for line in lines if line.strip()]

        new_content = ["""from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime, date, time
from sqlalchemy import text, String
from sqlalchemy.dialects.mysql import TINYINT
"""]

        in_class = False
        current_class = []
        tablename_added = False

        for i, line in enumerate(lines):
            print(f"DEBUG: Processing line -> {line.strip()}, in_class:{in_class}")

            if any(
                prefix in line for prefix in ["from sqlalchemy", "from typing", "declarative_base", "Base =", "class Base"]
            ):
                continue

            if line.strip().startswith("class ") and "Base)" in line:
                print(f"DEBUG: Found class definition -> {line.strip()}")
                in_class = True
                class_name = line.split("class ")[1].split("(")[0]
                current_class = [f"class {class_name}(SQLModel, table=True):"]
                tablename_added = False
                continue

            if in_class:
                if "__tablename__" in line:
                    print(f"DEBUG: Found __tablename__ -> {line.strip()}")
                    current_class.append("    " + line.strip())
                    tablename_added = True
                elif "mapped_column" in line:
                    print(f"DEBUG: Found mapped_column -> {line.strip()}")
                    converted_line = parse_mapped_column(line)
                    current_class.append(converted_line)

            # Detect end of class (next non-indented line that is not a comment)
            if in_class and i < len(lines) - 1:
                next_line = lines[i + 1]
                if next_line.strip() and not next_line.startswith(" "):
                    if not tablename_added:
                        current_class.append("    # __tablename__ was not preserved")
                    new_content.extend(current_class)
                    new_content.append("")
                    in_class = False

        # Ensure last class is added
        if in_class:
            if not tablename_added:
                current_class.append("    # __tablename__ was not preserved")
            new_content.extend(current_class)
            new_content.append("")

        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(new_content))

        print("🚀 Successfully converted to SQLModel!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    process_model_file()
