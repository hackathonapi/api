from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
from google import genai
from google.genai import types

from .schemas import ImageAltResult, ImageInput


def _pick_api_key() -> str:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""


def _guess_mime_type(image_bytes: bytes, fallback: str = "image/jpeg") -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return fallback


def _coerce_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except Exception:
            pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _normalize_alt(alt: str) -> str:
    alt = (alt or "").strip()
    return re.sub(r"\s+", " ", alt)


def _enforce_alt_length(alt: str, long_desc: str | None) -> tuple[str, str | None, list[str]]:
    warnings: list[str] = []
    alt = _normalize_alt(alt)
    if len(alt) <= 125:
        return alt, long_desc, warnings

    warnings.append("alt_truncated_to_125_chars")
    full = alt
    alt = full[:125].rstrip()
    if not long_desc:
        long_desc = full
    return alt, long_desc, warnings


@dataclass
class GeminiAltConfig:
    model: str = "gemini-2.5-flash"
    temperature: float = 0.1
    max_image_bytes: int = 10 * 1024 * 1024


def _build_prompt(doc_title: str | None, section_heading: str | None, before: str | None, after: str | None) -> str:
    context = []
    if doc_title:
        context.append(f"Document title: {doc_title}")
    if section_heading:
        context.append(f"Section heading: {section_heading}")
    if before:
        context.append(f"Text before image: {before}")
    if after:
        context.append(f"Text after image: {after}")

    ctx = "\n".join(context) if context else "No surrounding context provided."
    return f"""
You generate accessibility descriptions for a document image.
Return STRICT JSON only (no markdown, no extra text), with keys:
- alt (string, <=125 chars, concise, objective, avoid phrase 'image of')
- long_desc (string|null, required if chart/diagram or information dense)
- contains_text (boolean)
- is_chart_or_diagram (boolean)
- confidence (number 0..1)

Rules:
- If chart/diagram: include trend + key values/anomalies.
- If image contains text: summarize text topic, do not transcribe everything.
- No speculation about intent or identity.

Context:
{ctx}
""".strip()


async def _fetch_image_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


async def generate_alt_for_one(
    image: ImageInput,
    *,
    doc_title: str | None,
    section_heading: str | None,
    cfg: GeminiAltConfig,
) -> ImageAltResult:
    api_key = _pick_api_key()
    if not api_key:
        return ImageAltResult(
            image_id=image.image_id,
            alt="",
            confidence=0.0,
            warnings=["missing_GEMINI_API_KEY_or_GOOGLE_API_KEY"],
        )

    warnings: list[str] = []

    try:
        if image.data_base64:
            image_bytes = base64.b64decode(image.data_base64)
        else:
            image_bytes = await _fetch_image_bytes(str(image.url))
    except Exception:
        return ImageAltResult(
            image_id=image.image_id,
            alt="",
            confidence=0.0,
            warnings=["image_fetch_or_decode_failed"],
        )

    if not image_bytes:
        return ImageAltResult(
            image_id=image.image_id,
            alt="",
            confidence=0.0,
            warnings=["empty_image_bytes"],
        )

    if len(image_bytes) > cfg.max_image_bytes:
        return ImageAltResult(
            image_id=image.image_id,
            alt="",
            confidence=0.0,
            warnings=["image_too_large"],
        )

    mime = image.mime_type or _guess_mime_type(image_bytes)
    prompt = _build_prompt(doc_title, section_heading, image.context_before, image.context_after)

    client = genai.Client(api_key=api_key)
    response = await client.aio.models.generate_content(
        model=cfg.model,
        contents=[types.Part.from_text(prompt), types.Part.from_bytes(data=image_bytes, mime_type=mime)],
        config=types.GenerateContentConfig(temperature=cfg.temperature),
    )

    raw = (response.text or "").strip()
    parsed = _coerce_json(raw)

    if not parsed:
        alt, long_desc, extra = _enforce_alt_length(raw, None)
        return ImageAltResult(
            image_id=image.image_id,
            alt=alt,
            long_desc=long_desc,
            confidence=0.4,
            warnings=["gemini_non_json_fallback", *extra],
        )

    alt = str(parsed.get("alt", "") or "")
    long_desc = parsed.get("long_desc")
    contains_text = bool(parsed.get("contains_text", False))
    is_chart = bool(parsed.get("is_chart_or_diagram", False))
    confidence = float(parsed.get("confidence", 0.7) or 0.7)

    alt, long_desc, extra = _enforce_alt_length(alt, long_desc if isinstance(long_desc, str) else None)
    warnings.extend(extra)

    return ImageAltResult(
        image_id=image.image_id,
        alt=alt,
        long_desc=long_desc,
        contains_text=contains_text,
        is_chart_or_diagram=is_chart,
        confidence=max(0.0, min(1.0, confidence)),
        warnings=warnings,
    )


async def generate_alt_batch(
    images: list[ImageInput],
    *,
    doc_title: str | None,
    section_heading: str | None,
    model: str = "gemini-2.5-flash",
    max_image_bytes: int = 10 * 1024 * 1024,
) -> list[ImageAltResult]:
    cfg = GeminiAltConfig(model=model, max_image_bytes=max_image_bytes)
    tasks = [
        generate_alt_for_one(
            img,
            doc_title=doc_title,
            section_heading=section_heading,
            cfg=cfg,
        )
        for img in images
    ]
    return await asyncio.gather(*tasks)
