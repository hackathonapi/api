from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .routers.extract import router as extract_router
from .routers.summarizer import router as summarizer_router
from .routers.clearview import router as clearview_router

app = FastAPI(title="Clearway API")

app.include_router(extract_router)
app.include_router(summarizer_router)
app.include_router(clearview_router)

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
app.mount("/ui/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="ui-assets")

@app.get("/")
def root():
    return {"message": "API is running!"}


@app.get("/ui")
def ui_home():
    return RedirectResponse(url="/ui/")


@app.get("/ui/")
def ui_home_slash():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/ui/docs")
def ui_docs():
    return RedirectResponse(url="/ui/docs.html")


@app.get("/ui/docs.html")
def ui_docs_html():
    return FileResponse(FRONTEND_DIR / "docs.html")
