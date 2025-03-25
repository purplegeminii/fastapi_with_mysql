from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime, date, time
from sqlalchemy import text, String
from sqlalchemy.dialects.mysql import TINYINT

class Todo(SQLModel, table=True):
    __tablename__ = 'todo'
    item_id: int = Field(primary_key=True)
    todotext: Optional[str] = Field(max_length=255)
    is_done: Optional[bool] = Field(default=False)
