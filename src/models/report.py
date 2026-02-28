from typing import Literal, Optional  # Optional kept for ReportResponse.extraction_error

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    input: str
    method: Literal["openai", "sumy", "auto"] = Field(default="auto")
    sentence_count: int = Field(default=5, ge=1, le=20)


class ReportResponse(BaseModel):
    # From ExtractionResult
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    extraction_error: Optional[str]
    # From SummarizeResponse
    summary: str
    summarization_method: Literal["openai", "sumy"]
    sentence_count: int
    original_length: int
    summary_length: int
