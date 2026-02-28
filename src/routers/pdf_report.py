import asyncio

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from ..models.extract import ExtractRequest
from ..models.scam_detection import ScamDetectionRequest
from ..models.pdf_report import PdfReportRequest
from ..services.extractor_service import extract
from ..services.summarizer_service import summarize
from ..services.scam_detection_service import detect_scam
from ..services.pdf_service import generate_pdf

router = APIRouter(prefix="/pdf", tags=["PDF Report"])


@router.post("", response_class=Response)
async def generate_pdf_route(request: ExtractRequest) -> Response:
    # 1. Extract content
    try:
        extraction = await extract(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if extraction.error or not extraction.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=extraction.error or "Could not extract content.",
        )

    # 2. Summarize + scam detect in parallel
    summary_coro = summarize(extraction.content, "auto", 3)
    scam_coro = detect_scam(ScamDetectionRequest(input=extraction.content[:10_000]))
    summary_result, scam_result = await asyncio.gather(summary_coro, scam_coro, return_exceptions=True)

    summary = summary_result[0] if isinstance(summary_result, tuple) else None
    scam = scam_result if not isinstance(scam_result, Exception) else None

    # 3. Build PDF
    pdf_request = PdfReportRequest(
        title=extraction.title,
        authors=extraction.authors,
        content=extraction.content,
        source=extraction.source,
        word_count=extraction.word_count,
        extraction_method=extraction.extraction_method,
        summary=summary,
        scam_level=scam.level if scam else None,
        scam_score=scam.score if scam else None,
        scam_reasons=scam.reasons if scam else None,
    )

    try:
        pdf_bytes = await asyncio.to_thread(generate_pdf, pdf_request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {exc}",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=clearway_report.pdf"},
    )
