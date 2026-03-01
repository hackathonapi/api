from fastapi import APIRouter, HTTPException, status

from ..models.extract import ExtractRequest
from ..models.scam import ScamRequest, ScamResponse
from ..services.extractor_service import extract
from ..services.scam_service import detect_scam

router = APIRouter(prefix="/scam", tags=["Scam"])


@router.post(
    "",
    response_model=ScamResponse,
    summary="Detect scam/phishing probability",
    description=(
        "Extracts text from URL or raw input, runs a HuggingFace scam classifier, and "
        "optionally runs an OpenAI review when scam probability is above threshold."
    ),
)
async def analyze_scam(request: ScamRequest) -> ScamResponse:
    # Step 1: Extract text
    try:
        extraction = await extract(ExtractRequest(input=request.input))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if extraction.error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extraction failed: {extraction.error}",
        )

    # Step 2: Run scam classifier and optional review
    try:
        result = await detect_scam(
            text=extraction.content,
            threshold=request.threshold,
            review_with_llm=request.review_with_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scam analysis failed: {exc}",
        )

    return ScamResponse(
        content=extraction.content,
        input_type=extraction.input_type,
        source=extraction.source,
        word_count=extraction.word_count,
        extraction_method=extraction.extraction_method,
        extraction_error=extraction.error,
        scam_probability=result.scam_probability,
        non_scam_probability=result.non_scam_probability,
        predicted_label=result.predicted_label,
        is_scam=result.is_scam,
        threshold=result.threshold,
        scam_method=result.method_used,
        raw_scores=result.raw_scores,
        llm_review=result.llm_review,
        llm_review_model=result.llm_review_model,
        notes=result.notes,
        original_length=len(extraction.content),
    )
