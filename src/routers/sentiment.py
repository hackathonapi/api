from fastapi import APIRouter, HTTPException, status

from ..models.extract import ExtractRequest
from ..models.sentiment import SentimentRequest, SentimentResponse
from ..services.extractor_service import extract
from ..services.sentiment_service import analyze_sentiment

router = APIRouter(prefix="/sentiment", tags=["Sentiment"])


@router.post(
    "",
    response_model=SentimentResponse,
    summary="Analyze sentiment and bias signals",
    description=(
        "Extracts text from input (URL or raw text) and runs sentiment/tone analysis. "
        "Uses ModernBERT bias classification plus a short LLM explanation, with rule-based fallback."
    ),
)
async def analyze_tone(request: SentimentRequest) -> SentimentResponse:
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

    # Step 2: Analyze sentiment and bias tone
    try:
        result = await analyze_sentiment(
            text=extraction.content,
            method=request.method,
            bias_cutoff=request.bias_cutoff,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment analysis failed: {exc}",
        )

    return SentimentResponse(
        content=extraction.content,
        input_type=extraction.input_type,
        source=extraction.source,
        word_count=extraction.word_count,
        extraction_method=extraction.extraction_method,
        extraction_error=extraction.error,
        tone=result.tone,
        bias_risk=result.bias_risk,
        sentiment_score=result.sentiment_score,
        confidence=result.confidence,
        sentiment_method=result.method_used,
        bias_cutoff=result.bias_cutoff,
        bias_scores=result.bias_scores,
        biases_above_cutoff=result.biases_above_cutoff,
        bias_explanation=result.bias_explanation,
        signals=result.signals,
        notes=result.notes,
        original_length=len(extraction.content),
    )
