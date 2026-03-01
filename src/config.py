from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_turbo_v2_5"


settings = Settings()
