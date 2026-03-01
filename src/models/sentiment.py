from typing import Literal, Optional

from pydantic import BaseModel, Field


SentimentMethod = Literal["hf_modernbert_bias", "rule_based", "auto"]
SentimentMethodUsed = Literal["hf_modernbert_bias", "rule_based"]
ToneLabel = Literal["positive", "negative", "neutral", "mixed"]
BiasRisk = Literal["low", "medium", "high"]


class SentimentRequest(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        description="Raw text or URL input to extract and analyze.",
    )
    method: SentimentMethod = Field(
        default="auto",
        description=(
            "'hf_modernbert_bias' uses cirimus/modernbert-large-bias-type-classifier. "
            "'rule_based' uses a local heuristic analyzer. "
            "'auto' runs the ModernBERT bias classifier first, then falls back to rule-based."
        ),
    )
    bias_cutoff: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Bias scores at or above this threshold are included in the final explanation.",
    )


class BiasSignals(BaseModel):
    loaded_language_hits: int = Field(default=0, ge=0)
    absolutist_language_hits: int = Field(default=0, ge=0)
    first_person_hits: int = Field(default=0, ge=0)
    subjectivity_score: float = Field(default=0.0, ge=0.0, le=1.0)


class SentimentAnalysisResult(BaseModel):
    tone: ToneLabel
    bias_risk: BiasRisk
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    method_used: SentimentMethodUsed
    bias_cutoff: float = Field(ge=0.0, le=1.0)
    bias_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-bias score map from classifier output.",
    )
    biases_above_cutoff: list[str] = Field(
        default_factory=list,
        description="Bias labels whose scores are >= bias_cutoff.",
    )
    bias_explanation: str = Field(
        default="",
        description="3-4 sentence explanation describing how the selected biases appear in the text.",
    )
    signals: BiasSignals
    notes: Optional[str] = None


class SentimentResponse(BaseModel):
    # From ExtractionResult
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    extraction_error: Optional[str]
    # Sentiment output
    tone: ToneLabel
    bias_risk: BiasRisk
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    sentiment_method: SentimentMethodUsed
    bias_cutoff: float = Field(ge=0.0, le=1.0)
    bias_scores: dict[str, float] = Field(default_factory=dict)
    biases_above_cutoff: list[str] = Field(default_factory=list)
    bias_explanation: str = ""
    signals: BiasSignals
    notes: Optional[str] = None
    original_length: int
