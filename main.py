import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import aiomysql
from aiomysql import Connection, Cursor
from dotenv import load_dotenv
from models import Todo

load_dotenv()

app = FastAPI()


async def get_db():
    async with aiomysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DATABASE")
    ) as conn:
        yield conn


# class Item(BaseModel):
#     item_id: int
#     todotext: str = None
#     is_done: bool = False


@app.get('/')
def root():
    return {"hello": "world"}

@app.post('/items', response_model=Todo)
async def create_item(item: Todo, db: Connection = Depends(get_db)):
    async with db.cursor() as cur:
        cur: Cursor
        await cur.execute(
            "INSERT INTO todo (todotext, is_done) VALUES (%s, %s)",
            (item.todotext, item.is_done,)
        )
        item_id = cur.lastrowid
        await db.commit()
    return {"item_id":item_id, **item.model_dump()}


@app.get('/items', response_model=list[Todo])
async def list_items(limit: int = 10, db: Connection = Depends(get_db)):
    async with db.cursor() as cur:
        cur: Cursor
        await cur.execute("SELECT item_id, todotext, is_done FROM todo LIMIT %s", (limit,))
        rows = await cur.fetchall()
    
    return [{"item_id": row[0], "todotext": row[1], "is_done": bool(row[2])} for row in rows]


@app.get('/items/{item_id}', response_model=Todo)
async def get_item(item_id: int, db: Connection = Depends(get_db)):
    async with db.cursor() as cur:
        cur: Cursor
        await cur.execute("SELECT todotext, is_done FROM todo WHERE item_id = %s", (item_id,))
        row = await cur.fetchone()
    
    if row is None:
        raise HTTPException(status_code=404, detail=f"Item with id:{item_id} does not exist")
    
    return {"item_id": item_id, "todotext": row[0], "is_done": bool(row[1])}

@app.delete('/items/{item_id}', response_model=Todo)
async def delete_item(item_id: int, db: Connection = Depends(get_db)):
    async with db.cursor() as cur:
        cur: Cursor
        await cur.execute("DELETE FROM todo WHERE item_id = %s", (item_id,))
        rows_affected = cur.rowcount
        await db.commit()
    
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail=f"Item with id:{item_id} does not exist")
    
    return {"message": f"Item with id:{item_id} deleted successfully"}
