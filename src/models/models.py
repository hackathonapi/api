from typing import Optional

from pydantic import BaseModel, Field


class InputRequest(BaseModel):
    input: str


class AudioRequest(BaseModel):
    input: str
    voice_id: Optional[str] = None


class ExtractionResult(BaseModel):
    title: str
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    error: Optional[str]


class ObjectivityAnalysisResult(BaseModel):
    subjective_probability: float = Field(ge=0.0, le=1.0)
    objective_probability: float = Field(ge=0.0, le=1.0)
    is_subjective: bool
    notes: Optional[str] = None
    error: Optional[str]


class ScamAnalysisResult(BaseModel):
    scam_probability: float = Field(ge=0.0, le=1.0)
    non_scam_probability: float = Field(ge=0.0, le=1.0)
    is_scam: bool
    notes: Optional[str] = None
    error: Optional[str]


class SentimentAnalysisResult(BaseModel):
    bias_cutoff: float = Field(ge=0.0, le=1.0)
    bias_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-bias score map from classifier output.",
    )
    biases_above_cutoff: list[str] = Field(
        default_factory=list,
        description="Bias labels whose scores are >= bias_cutoff.",
    )
    notes: Optional[str] = None
    error: Optional[str]


class ClearviewResponse(BaseModel):
    title: str
    content: str
    source: str
    word_count: int
    summary: Optional[str]
    is_scam: bool
    scam_notes: Optional[str] = None
    is_subjective: bool
    subjective_notes: Optional[str] = None
    biases: list[str] = Field(
        default_factory=list,
        description="Bias labels whose scores are >= bias_cutoff.",
    )
    bias_notes: Optional[str] = None
    pdf: str = Field(description="Base64-encoded PDF of the Clearview report.")
    error: Optional[str]
