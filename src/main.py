import nltk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .routers.clearview import router as clearview_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    yield


app = FastAPI(title="Clearway API", lifespan=lifespan)

app.include_router(clearview_router)

@app.get("/")
def root():
    return {"message": "API is running!"}
