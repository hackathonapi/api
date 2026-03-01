from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .routers.clearview import router as clearview_router
from .routers.audio import router as audio_router

app = FastAPI(title="Clearway API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clearview_router)
app.include_router(audio_router)

@app.get("/")
def root():
    return {"message": "API is running!"}
