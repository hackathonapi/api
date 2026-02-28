from fastapi import FastAPI, Query

from .extractor import extract, ExtractRequest, ExtractionResult

app = FastAPI()


@app.get("/")
def root():
    return {"message": "API is running!"}


@app.get("/extract", response_model=ExtractionResult)
async def extract_get(url: str = Query(None), text: str = Query(None)) -> ExtractionResult:
    return await extract(ExtractRequest(url=url, text=text))


@app.post("/extract", response_model=ExtractionResult)
async def extract_post(request: ExtractRequest) -> ExtractionResult:
    return await extract(request)