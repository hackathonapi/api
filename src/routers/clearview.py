import asyncio
import base64
import logging

from fastapi import APIRouter, HTTPException, status

from ..models.models import ClearviewResponse, InputRequest
from ..services.extractor_service import extract
from ..services.analysis_service import analyze, AnalysisResult
from ..services.clearview_service import generate_clearview

router = APIRouter(tags=["Clearview"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# POST /clearview
# Extract → Unified analysis → Generate PDF
# ─────────────────────────────────────────────

@router.post("/clearview", response_model=ClearviewResponse)
async def clearview_route(request: InputRequest) -> ClearviewResponse:
    # 1. Extract
    try:
        extraction = await extract(request.input)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Unhandled extraction error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {exc}",
        )

    if extraction.error or not extraction.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=extraction.error or "Could not extract content.",
        )

    # 2. Run unified analysis (summarize + scam + objectivity + bias in one call)
    sentence_count = max(1, min(extraction.word_count // 100, 20))
    try:
        result = await analyze(extraction.content, sentence_count)
    except Exception as exc:
        logger.warning("Analysis failed: %s", exc)
        result = AnalysisResult()

    # 3. Build response fields
    title            = extraction.title or "Raw Text Clearview"
    summary_text     = result.summary
    scam_notes       = result.scam_notes
    subjective_notes = result.subjective_notes
    bias_notes       = result.bias_notes

    # 4. Generate PDF
    try:
        pdf_bytes = await asyncio.to_thread(
            generate_clearview,
            extraction.title,
            extraction.content,
            extraction.source,
            extraction.word_count,
            summary_text,
            scam_notes,
            subjective_notes,
            bias_notes,
            result.ai_sections,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clearview generation failed: {exc}",
        )

    ai_section = (
        "\n\n".join(f"{name}\n{text}" for name, text in result.ai_sections.items())
        if result.ai_sections else None
    )

    return ClearviewResponse(
        title=title,
        content=extraction.content,
        source=extraction.source,
        word_count=extraction.word_count,
        summary=summary_text,
        scam_notes=scam_notes,
        subjective_notes=subjective_notes,
        bias_notes=bias_notes,
        ai_section=ai_section,
        pdf=base64.b64encode(pdf_bytes).decode(),
        error=None,
    )
