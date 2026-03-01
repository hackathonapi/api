from fastapi import APIRouter, HTTPException, status

from ..models.extract import ExtractRequest
from ..models.objectivity import ObjectivityRequest, ObjectivityResponse
from ..services.extractor_service import extract
from ..services.objectivity_service import detect_objectivity

router = APIRouter(prefix="/objectivity", tags=["Objectivity"])


@router.post(
    "",
    response_model=ObjectivityResponse,
    summary="Classify text as subjective vs objective",
    description=(
        "Extracts text from URL or raw input and runs a HuggingFace classifier to "
        "estimate subjective vs objective probability."
    ),
)
async def analyze_objectivity(request: ObjectivityRequest) -> ObjectivityResponse:
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

    # Step 2: Run objectivity classifier
    try:
        result = await detect_objectivity(
            text=extraction.content,
            threshold=request.threshold,
            review_with_llm=request.review_with_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Objectivity analysis failed: {exc}",
        )

    return ObjectivityResponse(
        content=extraction.content,
        input_type=extraction.input_type,
        source=extraction.source,
        word_count=extraction.word_count,
        extraction_method=extraction.extraction_method,
        extraction_error=extraction.error,
        subjective_probability=result.subjective_probability,
        objective_probability=result.objective_probability,
        predicted_label=result.predicted_label,
        is_subjective=result.is_subjective,
        threshold=result.threshold,
        objectivity_method=result.method_used,
        raw_scores=result.raw_scores,
        llm_review=result.llm_review,
        llm_review_model=result.llm_review_model,
        notes=result.notes,
        original_length=len(extraction.content),
    )
