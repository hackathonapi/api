from typing import Literal, Optional

from pydantic import BaseModel, Field


class PdfReportRequest(BaseModel):
    title: str = ""
    authors: list[str] = []
    content: str = Field(..., min_length=1)
    source: str = ""
    word_count: int = 0
    extraction_method: str = ""
    summary: Optional[str] = None
    scam_level: Optional[Literal["safe", "suspicious", "high_risk"]] = None
    scam_score: Optional[int] = None
    scam_reasons: Optional[list[str]] = None
