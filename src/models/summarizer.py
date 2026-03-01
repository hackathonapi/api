from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        description="A URL to fetch and summarize, or a plain text block to summarize directly.",
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
