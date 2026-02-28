from fastapi import APIRouter, HTTPException, status

from ..models.summarizer import SummarizeRequest, SummarizeResponse
from ..services.summarizer_service import summarize

router = APIRouter(prefix="/summarize", tags=["Summarizer"])

@router.post(
    "",
    response_model=SummarizeResponse,
    summary="Summarize text",
    description="Accepts a block of text (e.g., a YouTube transcript) and returns a summary using OpenAI.",
)
async def summarize_text(request: SummarizeRequest) -> SummarizeResponse:
    summary, error = await summarize(
        text=request.text,
        sentence_count=request.sentence_count,
    )

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Summarization failed: {error}",
        )

    return SummarizeResponse(
        summary=summary,
        method_used="openai",
    )
