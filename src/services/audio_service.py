import logging
import os
from typing import Optional

from elevenlabs.client import AsyncElevenLabs
from elevenlabs.core import ApiError

from ..models.models import ExtractionResult
from ..services.extractor_service import extract

logger = logging.getLogger(__name__)

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel — clear neutral narration
MAX_CHARS = 5_000  # ElevenLabs practical per-request limit


async def generate_audio(input: str, voice_id: Optional[str] = None) -> tuple[bytes, ExtractionResult]:
    if not os.environ.get('ELEVENLABS_AI_KEY'):
        raise ValueError("ELEVENLABS_API_KEY is not configured.")

    # Extract text from URL or plain text input
    result = await extract(input)
    if result.error:
        raise ValueError(result.error)

    text = result.content
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    client = AsyncElevenLabs(api_key=os.environ.get('ELEVENLABS_AI_KEY'))
    resolved_voice = voice_id or DEFAULT_VOICE_ID

    try:
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=resolved_voice,
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128",
        )
        chunks = []
        async for chunk in audio_stream:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
        return b"".join(chunks), result

    except ApiError as exc:
        logger.error("ElevenLabs API error: %s %s", exc.status_code, exc.body)
        raise RuntimeError(f"ElevenLabs API error ({exc.status_code})") from exc
    except Exception as exc:
        logger.error("ElevenLabs request failed: %s", exc)
        raise RuntimeError(f"ElevenLabs request failed: {exc}") from exc
