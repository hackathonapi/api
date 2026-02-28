from fastapi import FastAPI, HTTPException, Query

from .extractor import extract, ExtractRequest, ExtractionResult

app = FastAPI()


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