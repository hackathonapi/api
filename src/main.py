from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# --- Models ---
class Item(BaseModel):
    name: str
    description: str

# --- Routes ---

@app.get("/")
def root():
    return {"message": "API is running!"}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"item_id": item_id, "name": "Sample Item"}


@app.post("/items")
def create_item(item: Item):
    # Your logic here — e.g. save to DB, process, etc.
    return {"message": "Item created!", "item": item}
