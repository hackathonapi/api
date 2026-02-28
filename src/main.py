from fastapi import FastAPI, Query

from .extractor import extract, ExtractRequest, ExtractionResult
from src.routers.summarizer import router as summarizer_router
from src.routers.report import router as report_router

app = FastAPI(title="Clearway API")

app.include_router(summarizer_router)
app.include_router(report_router)

@app.get("/")
def root():
    return {"message": "API is running!"}


@app.get("/extract", response_model=ExtractionResult)
async def extract_get(url: str = Query(None), text: str = Query(None)) -> ExtractionResult:
    return await extract(ExtractRequest(url=url, text=text))
