from typing import Literal, Optional

from pydantic import BaseModel, Field


ObjectivityMethodUsed = Literal["hf_subjectivity_classifier"]
ObjectivityLabel = Literal["SUBJECTIVE", "OBJECTIVE"]


class ObjectivityRequest(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        description="Raw text or URL input to extract and analyze for subjectivity/objectivity.",
    )
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="If subjective_probability >= threshold, is_subjective will be true.",
    )
    review_with_llm: bool = Field(
        default=True,
        description=(
            "When true, run an OpenAI advisory note if text is classified as subjective "
            "at or above the threshold."
        ),
    )


class ObjectivityAnalysisResult(BaseModel):
    subjective_probability: float = Field(ge=0.0, le=1.0)
    objective_probability: float = Field(ge=0.0, le=1.0)
    predicted_label: ObjectivityLabel
    is_subjective: bool
    threshold: float = Field(ge=0.0, le=1.0)
    method_used: ObjectivityMethodUsed
    raw_scores: dict[str, float] = Field(default_factory=dict)
    llm_review: Optional[str] = None
    llm_review_model: Optional[str] = None
    notes: Optional[str] = None


class ObjectivityResponse(BaseModel):
    # From ExtractionResult
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    extraction_error: Optional[str]
    # Objectivity output
    subjective_probability: float = Field(ge=0.0, le=1.0)
    objective_probability: float = Field(ge=0.0, le=1.0)
    predicted_label: ObjectivityLabel
    is_subjective: bool
    threshold: float = Field(ge=0.0, le=1.0)
    objectivity_method: ObjectivityMethodUsed
    raw_scores: dict[str, float] = Field(default_factory=dict)
    llm_review: Optional[str] = None
    llm_review_model: Optional[str] = None
    notes: Optional[str] = None
    original_length: int
