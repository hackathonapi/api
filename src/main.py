# Imports
from fastapi import FastAPI

# Initializes our API
app = FastAPI()

# Routes
@app.get("/")
def read_root():
    return {"Hello": "World"}