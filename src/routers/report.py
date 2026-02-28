from fastapi import APIRouter, HTTPException, status

from src.extractor import extract, ExtractRequest
from src.models.report import ReportRequest, ReportResponse
from src.services.summarizer_service import summarize

router = APIRouter(prefix="/report", tags=["Report"])


@router.post("", response_model=ReportResponse)
async def generate_report(request: ReportRequest) -> ReportResponse:
    # Step 1: Extract
    extraction = await extract(ExtractRequest(url=request.url, text=request.text))
    if extraction.error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extraction failed: {extraction.error}",
        )

    # Step 2: Summarize
    try:
        summary, method_used = await summarize(
            text=extraction.content,
            method=request.method,
            sentence_count=request.sentence_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {exc}",
        )

    return ReportResponse(
        content=extraction.content,
        input_type=extraction.input_type,
        source=extraction.source,
        word_count=extraction.word_count,
        extraction_method=extraction.extraction_method,
        extraction_error=extraction.error,
        summary=summary,
        summarization_method=method_used,
        sentence_count=request.sentence_count,
        original_length=len(extraction.content),
        summary_length=len(summary),
    )
