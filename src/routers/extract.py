from fastapi import APIRouter, HTTPException, Query

from ..models.extract import ExtractRequest, ExtractionResult
from ..services.extractor_service import extract

router = APIRouter(prefix="/extract", tags=["Extract"])


@router.get("", response_model=ExtractionResult)
async def extract_get(input: str = Query(...)) -> ExtractionResult:
    try:
        return await extract(ExtractRequest(input=input))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("", response_model=ExtractionResult)
async def extract_post(request: ExtractRequest) -> ExtractionResult:
    try:
        return await extract(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
