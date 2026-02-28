from fastapi import FastAPI, HTTPException, Query

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
async def extract_get(input: str = Query(...)) -> ExtractionResult:
    try:
        return await extract(ExtractRequest(input=input))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/extract", response_model=ExtractionResult)
async def extract_post(request: ExtractRequest) -> ExtractionResult:
    try:
        return await extract(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
