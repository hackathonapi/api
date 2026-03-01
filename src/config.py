from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    hf_bias_model_id: str = "cirimus/modernbert-large-bias-type-classifier"
    bias_explainer_model: str = "gpt-4o-mini"
    bias_cutoff_default: float = 0.7
    bias_explanation_max_sentences: int = 4
    hf_scam_model_id: str = "BothBosu/bert-scam-classifier-v1.6"
    scam_threshold_default: float = 0.5
    scam_reviewer_model: str = "gpt-4o-mini"
    scam_review_max_sentences: int = 4
    hf_objectivity_model_id: str = "GroNLP/mdebertav3-subjectivity-english"
    objectivity_threshold_default: float = 0.5
    objectivity_reviewer_model: str = "gpt-4o-mini"
    objectivity_review_max_sentences: int = 4

    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_turbo_v2_5"


settings = Settings()
