from typing import Literal

from pydantic import BaseModel, Field


class ScamDetectionRequest(BaseModel):
    input: str = Field(..., min_length=10)


class ScamDetectionResult(BaseModel):
    level: Literal["safe", "suspicious", "high_risk"]
    score: int = Field(description="0 (safe) to 100 (definite scam)")
    reasons: list[str]
    method: Literal["gemini", "algorithmic"]
