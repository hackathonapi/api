from typing import Optional

from pydantic import BaseModel, Field

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel — clear neutral narration
MAX_CHARS = 5_000  # ElevenLabs practical per-request limit


class AudiobookRequest(BaseModel):
    input: str = Field(..., min_length=1, description="URL or plain text to convert to speech.")
    voice_id: Optional[str] = Field(default=DEFAULT_VOICE_ID)
