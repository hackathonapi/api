import asyncio
import io
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


def _gtts_fallback(text: str) -> bytes:
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang="en").write_to_fp(buf)
    return buf.getvalue()


async def generate_audio(input: str, voice_id: Optional[str] = None) -> tuple[bytes, ExtractionResult]:
    result = await extract(input)
    if result.error:
        raise ValueError(result.error)

    text = result.content
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if api_key:
        resolved_voice = voice_id or DEFAULT_VOICE_ID
        client = AsyncElevenLabs(api_key=api_key)
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
        except (ApiError, Exception) as exc:
            logger.warning("ElevenLabs failed (%s), falling back to gTTS.", exc)

    # Fallback: gTTS (Google TTS, free, no API key, outputs MP3 directly)
    logger.info("Generating audio with gTTS fallback.")
    mp3_bytes = await asyncio.to_thread(_gtts_fallback, text)
    return mp3_bytes, result
