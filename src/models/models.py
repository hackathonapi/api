from typing import Optional

from pydantic import BaseModel, Field


class InputRequest(BaseModel):
    input: str = Field(..., min_length=1)


class AudioRequest(BaseModel):
    input: str = Field(..., min_length=1)
    voice_id: Optional[str] = None


class ExtractionResult(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
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
    scam_notes: Optional[str] = None
    subjective_notes: Optional[str] = None
    bias_notes: Optional[str] = None
    ai_section: Optional[str] = None
    pdf: str = Field(description="Base64-encoded PDF of the Clearview report.")
    error: Optional[str]
