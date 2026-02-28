from typing import Literal

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=50,
        description="The text to summarize. Can be a YouTube transcript or any plain text block.",
    )
    sentence_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Target number of sentences in the summary.",
    )


class SummarizeResponse(BaseModel):
    summary: str
    method_used: str
