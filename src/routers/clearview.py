import asyncio
import base64
import logging
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from ..models.models import ClearviewResponse, InputRequest
from ..services.extractor_service import extract
from ..services.summarizer_service import summarize
from ..services.clearview_service import generate_clearview
from ..services.scam_service import detect_scam
from ..services.objectivity_service import detect_objectivity
from ..services.sentiment_service import analyze_sentiment
from ..services import firebase_service

router = APIRouter(tags=["Clearview"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# POST /clearview
# Extract → Parallel analysis → Generate PDF → Save to Firebase
# ─────────────────────────────────────────────

@router.post("/clearview", response_model=ClearviewResponse)
async def clearview_route(request: InputRequest) -> ClearviewResponse:
    # 1. Extract
    try:
        extraction = await extract(request.input)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if extraction.error or not extraction.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=extraction.error or "Could not extract content.",
        )

    # 2. Run summarize + scam + objectivity + sentiment in parallel
    sentence_count = max(1, min(extraction.word_count // 100, 20))
    results = await asyncio.gather(
        summarize(extraction.content, sentence_count),
        detect_scam(extraction.content),
        detect_objectivity(extraction.content),
        analyze_sentiment(extraction.content),
        return_exceptions=True,
    )

    summary_result, scam_result, objectivity_result, sentiment_result = results

    summary_text = summary_result[0] if not isinstance(summary_result, Exception) else None

    if isinstance(scam_result, Exception):
        logger.warning("Scam analysis failed: %s", scam_result)
        scam_result = None
    if isinstance(objectivity_result, Exception):
        logger.warning("Objectivity analysis failed: %s", objectivity_result)
        objectivity_result = None
    if isinstance(sentiment_result, Exception):
        logger.warning("Sentiment analysis failed: %s", sentiment_result)
        sentiment_result = None

    # 3. Build response fields
    record_id = str(uuid.uuid4())
    title = extraction.title or "Article Clearview"
    is_scam = scam_result.is_scam if scam_result else False
    scam_notes = scam_result.notes if scam_result else None
    is_subjective = objectivity_result.is_subjective if objectivity_result else False
    subjective_notes = objectivity_result.notes if objectivity_result else None
    biases = sentiment_result.biases_above_cutoff if sentiment_result else []
    bias_notes = sentiment_result.notes if sentiment_result else None

    # 4. Generate PDF
    try:
        pdf_bytes = await asyncio.to_thread(
            generate_clearview,
            extraction.title,
            extraction.content,
            extraction.source,
            extraction.word_count,
            summary_text,
            is_scam,
            scam_notes,
            is_subjective,
            subjective_notes,
            biases,
            bias_notes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clearview generation failed: {exc}",
        )

    # 5. Save full analysis to Firebase
    await firebase_service.save_clearway(
        record_id,
        {
            "title": title,
            "content": extraction.content,
            "word_count": extraction.word_count,
            "summary": summary_text,
            "is_scam": is_scam,
            "scam_notes": scam_notes,
            "is_subjective": is_subjective,
            "subjective_notes": subjective_notes,
            "biases": biases,
            "bias_notes": bias_notes,
        },
        pdf_bytes,
    )

    return ClearviewResponse(
        id=record_id,
        title=title,
        content=extraction.content,
        source=extraction.source,
        word_count=extraction.word_count,
        summary=summary_text,
        is_scam=is_scam,
        scam_notes=scam_notes,
        is_subjective=is_subjective,
        subjective_notes=subjective_notes,
        biases=biases,
        bias_notes=bias_notes,
        pdf=base64.b64encode(pdf_bytes).decode(),
        error=None,
    )


# ─────────────────────────────────────────────
# GET /clearview/{record_id}
# Download the PDF file for a previously generated Clearview
# ─────────────────────────────────────────────

@router.get("/clearview/{record_id}")
async def get_clearview_route(record_id: str) -> Response:
    meta, pdf_bytes = await firebase_service.get_clearway(record_id)
    filename = meta.get("title", record_id).replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )
