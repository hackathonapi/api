import nltk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .routers.extract import router as extract_router
from .routers.summarizer import router as summarizer_router
<<<<<<< HEAD
from .routers.clearview import router as clearview_router
from .routers.audiobook import router as audiobook_router
=======
from .routers.report import router as report_router
from .routers.sentiment import router as sentiment_router
from .routers.scam import router as scam_router
from .routers.objectivity import router as objectivity_router
>>>>>>> 2b915ed (sentiments)


@asynccontextmanager
async def lifespan(_: FastAPI):
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    yield


app = FastAPI(title="Clearway API", lifespan=lifespan)

app.include_router(extract_router)
app.include_router(summarizer_router)
<<<<<<< HEAD
app.include_router(clearview_router)
app.include_router(audiobook_router)
=======
app.include_router(report_router)
app.include_router(sentiment_router)
app.include_router(scam_router)
app.include_router(objectivity_router)

>>>>>>> 2b915ed (sentiments)

@app.get("/")
def root():
    return {"message": "API is running!"}