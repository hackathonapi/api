from fastapi import FastAPI

from .routers.extract import router as extract_router
from .routers.summarizer import router as summarizer_router
from .routers.report import router as report_router
from .routers.scam_detection import router as scam_router
from .routers.pdf_report import router as pdf_router

app = FastAPI(title="Clearway API")

app.include_router(extract_router)
app.include_router(summarizer_router)
app.include_router(report_router)
app.include_router(scam_router)
app.include_router(pdf_router)

@app.get("/")
def root():
    return {"message": "API is running!"}