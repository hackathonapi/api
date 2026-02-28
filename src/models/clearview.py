from typing import Optional

from pydantic import BaseModel, Field


class ClearviewData(BaseModel):
    title: str = ""
    content: str = Field(..., min_length=1)
    source: str = ""
    word_count: int = 0
    summary: Optional[str] = None


class ClearviewResponse(BaseModel):
    title: str
    content: str
    source: str
    word_count: int
    summary: Optional[str]
    pdf: str = Field(description="Base64-encoded PDF of the Clearview report.")
