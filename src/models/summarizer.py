from typing import Literal

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=50,
        description="The text to summarize. Can be a YouTube transcript or any plain text block.",
    )
    method: Literal["openai", "sumy", "auto"] = Field(
        default="auto",
        description=(
            "'openai' forces the OpenAI GPT backend. "
            "'sumy' forces the local extractive (LexRank) backend. "
            "'auto' tries OpenAI first and falls back to sumy on any failure."
        ),
    )
    sentence_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Target number of sentences in the summary.",
    )


class SummarizeResponse(BaseModel):
    summary: str
    method_used: Literal["openai", "sumy"]
    sentence_count: int
    original_length: int = Field(description="Character count of the input text.")
    summary_length: int = Field(description="Character count of the summary.")
