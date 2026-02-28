import asyncio
import base64

from fastapi import APIRouter, HTTPException, status

from ..models.extract import ExtractRequest
from ..models.clearview import ClearviewData, ClearviewResponse
from ..services.extractor_service import extract
from ..services.summarizer_service import summarize
from ..services.clearview_service import generate_clearview

router = APIRouter(prefix="/clearview", tags=["Clearview"])


@router.post("", response_model=ClearviewResponse)
async def generate_clearview_route(request: ExtractRequest) -> ClearviewResponse:
    # 1. Extract
    try:
        extraction = await extract(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if extraction.error or not extraction.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=extraction.error or "Could not extract content.",
        )

    # 2. Summarize
    summary_text, _ = await summarize(extraction.content, max(1, min(extraction.word_count / 100, 20)))

    # 3. Generate PDF
    data = ClearviewData(
        title=extraction.title,
        content=extraction.content,
        source=extraction.source,
        word_count=extraction.word_count,
        summary=summary_text,
    )

    try:
        pdf_bytes = await asyncio.to_thread(generate_clearview, data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clearview generation failed: {exc}",
        )

    return ClearviewResponse(
        title=data.title or "Article Clearview",
        content=data.content,
        source=data.source,
        word_count=data.word_count,
        summary=data.summary,
        pdf=base64.b64encode(pdf_bytes).decode(),
    )
