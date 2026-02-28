from __future__ import annotations

import base64
import os
import re
import uuid
from typing import Iterable

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from .schemas import TTSChunkResult


def _pick_eleven_key() -> str:
    return os.getenv("ELEVENLABS_API_KEY") or ""


def split_text_into_chunks(text: str, max_chars: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            sentences = [s.strip() for s in re.split(r"(?<=[。！？.!?])\s+", paragraph) if s.strip()]
            for sentence in sentences:
                if len(buf) + len(sentence) + 1 <= max_chars:
                    buf = f"{buf} {sentence}".strip()
                else:
                    flush()
                    buf = sentence
            flush()
            continue

        if len(buf) + len(paragraph) + 2 <= max_chars:
            buf = f"{buf}\n\n{paragraph}".strip()
        else:
            flush()
            buf = paragraph

    flush()
    return chunks


def _audio_iter_to_bytes(audio_iter: Iterable[bytes]) -> bytes:
    out = bytearray()
    for part in audio_iter:
        if part:
            out.extend(part)
    return bytes(out)


def tts_one_chunk(*, text: str, voice_id: str, model_id: str, output_format: str) -> bytes:
    api_key = _pick_eleven_key()
    if not api_key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY")

    client = ElevenLabs(api_key=api_key)
    audio_iter = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
        voice_settings=VoiceSettings(
            stability=0.2,
            similarity_boost=0.9,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )
    return _audio_iter_to_bytes(audio_iter)


def tts_many_chunks_base64(
    *,
    chunks: list[str],
    voice_id: str,
    model_id: str,
    output_format: str,
    return_base64: bool,
) -> list[TTSChunkResult]:
    results: list[TTSChunkResult] = []
    for idx, chunk in enumerate(chunks):
        chunk_id = f"chunk_{idx + 1:03d}_{uuid.uuid4().hex[:8]}"
        audio_bytes = tts_one_chunk(
            text=chunk,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
        )
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if return_base64 else None
        results.append(
            TTSChunkResult(
                chunk_id=chunk_id,
                num_chars=len(chunk),
                audio_base64=audio_b64,
            )
        )
    return results
