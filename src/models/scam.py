from typing import Literal, Optional

from pydantic import BaseModel, Field


ScamMethodUsed = Literal["hf_bert_scam_classifier_v1_6"]
ScamLabel = Literal["SCAM", "NON-SCAM"]


class ScamRequest(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        description="Raw text or URL input to extract and analyze for scam probability.",
    )
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="If scam_probability >= threshold, an LLM review is triggered.",
    )
    review_with_llm: bool = Field(
        default=True,
        description="When true, runs OpenAI review if scam_probability is above threshold.",
    )


class ScamAnalysisResult(BaseModel):
    scam_probability: float = Field(ge=0.0, le=1.0)
    non_scam_probability: float = Field(ge=0.0, le=1.0)
    predicted_label: ScamLabel
    is_scam: bool
    threshold: float = Field(ge=0.0, le=1.0)
    method_used: ScamMethodUsed
    raw_scores: dict[str, float] = Field(default_factory=dict)
    llm_review: Optional[str] = None
    llm_review_model: Optional[str] = None
    notes: Optional[str] = None


class ScamResponse(BaseModel):
    # From ExtractionResult
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    extraction_error: Optional[str]
    # Scam output
    scam_probability: float = Field(ge=0.0, le=1.0)
    non_scam_probability: float = Field(ge=0.0, le=1.0)
    predicted_label: ScamLabel
    is_scam: bool
    threshold: float = Field(ge=0.0, le=1.0)
    scam_method: ScamMethodUsed
    raw_scores: dict[str, float] = Field(default_factory=dict)
    llm_review: Optional[str] = None
    llm_review_model: Optional[str] = None
    notes: Optional[str] = None
    original_length: int
