from fastapi import FastAPI

from .routers.extract import router as extract_router
from .routers.summarizer import router as summarizer_router
from .routers.clearview import router as clearview_router

app = FastAPI(title="Clearway API")

app.include_router(extract_router)
app.include_router(summarizer_router)
app.include_router(clearview_router)

@app.get("/")
def root():
    return {"message": "API is running!"}
