from typing import Optional

from pydantic import BaseModel


class ExtractRequest(BaseModel):
    input: str


class ExtractionResult(BaseModel):
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    error: Optional[str]
