from fastapi import FastAPI

from .extractor import extract, ExtractRequest, ExtractionResult

app = FastAPI()


@app.get("/")
def root():
    return {"message": "API is running!"}


@app.post("/extract", response_model=ExtractionResult)
async def extract_route(request: ExtractRequest) -> ExtractionResult:
    return await extract(request)
