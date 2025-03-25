# FastAPI Todo App

A simple RESTful API for managing todo items built with FastAPI and MySQL.

## Project Overview

This application provides a lightweight API for creating, retrieving, and deleting todo items. It uses:

- **FastAPI** for API endpoints and request handling
- **SQLModel** for data modeling
- **aiomysql** for asynchronous database connections
- **MySQL** as the database backend

## Files

- `main.py` - Main application file with API routes and database connection logic
- `models.py` - SQLModel data models for the Todo items
- `generate_sqlmodels.py` - Utility for generating SQLModel classes from database schema
- `tests.py` - Tests for API endpoints

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install fastapi uvicorn aiomysql python-dotenv sqlmodel
```

3. Set up environment variables in a `.env` file:

```
MYSQL_HOST=localhost
MYSQL_USER=yourusername
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=todo_db
```

4. Create the database and todo table:

```sql
CREATE DATABASE todo_db;
USE todo_db;
CREATE TABLE todo (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    todotext VARCHAR(255),
    is_done BOOLEAN DEFAULT FALSE
);
```

## Running the Application

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The API will be available at: http://localhost:8000

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | / | Root endpoint - returns {"hello": "world"} |
| POST | /items | Create a new todo item |
| GET | /items | List all todo items (with optional limit parameter) |
| GET | /items/{item_id} | Get a specific todo item by ID |
| DELETE | /items/{item_id} | Delete a specific todo item by ID |

## API Usage Examples

### Create a new todo item

```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"todotext": "Buy groceries", "is_done": false}'
```

### List all todo items (with limit)

```bash
curl "http://localhost:8000/items?limit=5"
```

### Get a specific todo item

```bash
curl "http://localhost:8000/items/1"
```

### Delete a todo item

```bash
curl -X DELETE "http://localhost:8000/items/1"
```

## Database Model Generator

The project includes `generate_sqlmodels.py`, which can automatically generate SQLModel classes based on your existing database schema. This is useful for keeping your models in sync with the database structure.

Usage:

```bash
python generate_sqlmodels.py
```

## Testing

Run the tests to verify API functionality:

```bash
python -m pytest tests.py -v
```

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- Swagger UI: http://localhost:8000/docs#/
- ReDoc: http://localhost:8000/redoc

## License

MIT