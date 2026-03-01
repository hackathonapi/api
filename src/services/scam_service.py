import asyncio
import logging
import os
import re
from typing import Any

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..models.models import ScamAnalysisResult

logger = logging.getLogger(__name__)

_HF_SCAM_MODEL_ID = "BothBosu/bert-scam-classifier-v1.6"
_THRESHOLD = 0.5
_REVIEWER_MODEL = "gpt-4o-mini"

_scam_classifier: Any = None


def _chunk_text(text: str, max_chars: int = 1800) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks[:10]


def _load_classifier_sync():
    global _scam_classifier
    if _scam_classifier is not None:
        return _scam_classifier
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ValueError("transformers is required. Install dependencies from requirements.txt.") from exc
    _scam_classifier = pipeline(
        task="text-classification",
        model=_HF_SCAM_MODEL_ID,
        tokenizer=_HF_SCAM_MODEL_ID,
        device=-1,
        top_k=None,
    )
    return _scam_classifier


def _run_classifier_sync(text: str) -> tuple[float, float]:
    classifier = _load_classifier_sync()
    chunks = _chunk_text(text)
    raw = classifier(chunks, truncation=True, max_length=512)

    if raw and isinstance(raw[0], dict):
        raw = [raw]

    scam_scores: list[float] = []
    non_scam_scores: list[float] = []

    for batch in raw:
        row: dict[str, float] = {}
        for item in batch:
            label = str(item.get("label", "")).strip().upper().replace("_", "-")
            if label == "LABEL-1":
                label = "SCAM"
            elif label == "LABEL-0":
                label = "NON-SCAM"
            row[label] = float(item.get("score", 0.0))

        scam = row.get("SCAM", 0.0)
        non_scam = row.get("NON-SCAM", 0.0)
        if scam == 0.0 and non_scam > 0.0:
            scam = 1.0 - non_scam
        if non_scam == 0.0 and scam > 0.0:
            non_scam = 1.0 - scam
        total = scam + non_scam
        if total > 0:
            scam /= total
            non_scam /= total
        scam_scores.append(scam)
        non_scam_scores.append(non_scam)

    if not scam_scores:
        raise RuntimeError("Classifier returned no scores.")

    scam_prob = sum(scam_scores) / len(scam_scores)
    non_scam_prob = sum(non_scam_scores) / len(non_scam_scores)
    total = scam_prob + non_scam_prob
    if total > 0:
        scam_prob /= total
        non_scam_prob /= total
    else:
        scam_prob = 0.5
        non_scam_prob = 0.5

    return round(scam_prob, 4), round(non_scam_prob, 4)


def _fallback_notes(scam_probability: float, is_scam: bool) -> str:
    if is_scam:
        return (
            f"This content shows signs of being a scam or phishing attempt "
            f"(scam probability: {scam_probability:.0%}). "
            "Be cautious — do not click links, share personal information, or make payments "
            "without verifying with a trusted source first."
        )
    return (
        f"This content does not appear to be a scam (scam probability: {scam_probability:.0%}). "
        "It seems safe to engage with, though always exercise caution with unsolicited messages."
    )


async def _generate_notes(text: str, scam_probability: float, is_scam: bool) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _fallback_notes(scam_probability, is_scam)

    label = "likely a scam" if is_scam else "likely safe"
    user_prompt = (
        f"Scam probability: {scam_probability:.1%} ({label}).\n\n"
        f"Content:\n{text[:4000]}\n\n"
        "In 2-3 plain sentences, explain whether this content is safe or suspicious "
        "and what the reader should do."
    )

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=_REVIEWER_MODEL,
            temperature=0.2,
            max_tokens=180,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a security analysis assistant. Write for a general audience. "
                        "Use plain language, be calm and practical. Avoid alarmist wording."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except (AuthenticationError, RateLimitError, APIError, Exception) as exc:
        logger.warning("OpenAI scam notes failed (%s); using fallback.", exc)
        return _fallback_notes(scam_probability, is_scam)


async def detect_scam(text: str) -> ScamAnalysisResult:
    # TEMPORARILY DISABLED — models removed for deployment testing
    return ScamAnalysisResult(
        scam_probability=0.0,
        non_scam_probability=1.0,
        is_scam=False,
        notes="Scam analysis temporarily disabled.",
        error=None,
    )
