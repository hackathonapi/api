from typing import Optional

from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    title: str
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    error: Optional[str]


class ClearviewResponse(BaseModel):
    title: str
    content: str
    source: str
    word_count: int
    summary: Optional[str]
    pdf: str = Field(description="Base64-encoded PDF of the Clearview report.")
