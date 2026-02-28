from fastapi import APIRouter, HTTPException, status

from src.models.summarizer import SummarizeRequest, SummarizeResponse
from src.services.summarizer_service import summarize

router = APIRouter(prefix="/summarize", tags=["Summarizer"])


@router.post(
    "",
    response_model=SummarizeResponse,
    summary="Summarize text",
    description=(
        "Accepts a block of text (e.g., a YouTube transcript) and returns a summary. "
        "Supports OpenAI (GPT) and local extractive (LexRank via sumy) backends."
    ),
)
async def summarize_text(request: SummarizeRequest) -> SummarizeResponse:
    try:
        summary, method_used = await summarize(
            text=request.text,
            method=request.method,
            sentence_count=request.sentence_count,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {exc}",
        )

    return SummarizeResponse(
        summary=summary,
        method_used=method_used,
        sentence_count=request.sentence_count,
        original_length=len(request.text),
        summary_length=len(summary),
    )
