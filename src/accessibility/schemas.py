from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ImageInput(BaseModel):
    image_id: str = Field(..., description="Unique image id from extractor/frontend")
    mime_type: str | None = Field(None, description="e.g. image/png, image/jpeg")
    data_base64: str | None = Field(None, description="Base64 encoded image bytes")
    url: HttpUrl | None = Field(None, description="Image URL")
    context_before: str | None = Field(None, description="Optional nearby text before image")
    context_after: str | None = Field(None, description="Optional nearby text after image")

    @model_validator(mode="after")
    def validate_source(self) -> "ImageInput":
        if not self.data_base64 and not self.url:
            raise ValueError("Either data_base64 or url must be provided")
        return self


class ImageAltRequest(BaseModel):
    doc_title: str | None = None
    section_heading: str | None = None
    model: str = Field("gemini-2.5-flash", description="Gemini model name")
    max_image_bytes: int = Field(10 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    images: list[ImageInput]


class ImageAltResult(BaseModel):
    image_id: str
    alt: str = Field(..., description="<=125 chars preferred")
    long_desc: str | None = None
    contains_text: bool = False
    is_chart_or_diagram: bool = False
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class ImageAltResponse(BaseModel):
    images_alt: list[ImageAltResult]


class TTSRequest(BaseModel):
    text: str
    voice_id: str = Field("pNInz6obpgDQGcFmaJgB", description="ElevenLabs voice id")
    model_id: str = Field("eleven_turbo_v2_5", description="ElevenLabs model id")
    output_format: str = Field("mp3_22050_32", description="ElevenLabs output format")
    max_chars_per_chunk: int = Field(1200, ge=200, le=6000)
    return_base64: bool = Field(True)


class TTSChunkResult(BaseModel):
    chunk_id: str
    num_chars: int
    audio_mime_type: Literal["audio/mpeg"] = "audio/mpeg"
    audio_base64: str | None = None


class TTSResponse(BaseModel):
    script: str
    chunks: list[TTSChunkResult]


class DyslexiaSettings(BaseModel):
    enabled: bool = True
    font_family: str = "OpenDyslexic, Atkinson Hyperlegible, Arial, sans-serif"
    font_size_px: int = Field(18, ge=12, le=40)
    line_height: float = Field(1.6, ge=1.2, le=3.0)
    letter_spacing_em: float = Field(0.03, ge=0.0, le=0.2)
    word_spacing_em: float = Field(0.12, ge=0.0, le=0.5)
    max_width_ch: int = Field(80, ge=40, le=120)
    paragraph_spacing_em: float = Field(0.6, ge=0.0, le=2.0)


class DyslexiaRequest(BaseModel):
    settings: DyslexiaSettings = Field(default_factory=DyslexiaSettings)


class DyslexiaResponse(BaseModel):
    css: str
    recommended_settings: DyslexiaSettings
