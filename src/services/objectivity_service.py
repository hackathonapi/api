import asyncio
import logging
import os
import re
from typing import Any

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..models.models import ObjectivityAnalysisResult

_objectivity_classifier: Any = None
logger = logging.getLogger(__name__)

_HF_OBJECTIVITY_MODEL_ID = "GroNLP/mdebertav3-subjectivity-english"
_THRESHOLD = 0.5
_REVIEWER_MODEL = "gpt-4o-mini"


def _chunk_text(text: str, max_chars: int = 2000) -> list[str]:
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
    return chunks[:12]


def _load_classifier_sync():
    global _objectivity_classifier
    if _objectivity_classifier is not None:
        return _objectivity_classifier
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ValueError("transformers is required. Install dependencies from requirements.txt.") from exc
    _objectivity_classifier = pipeline(
        task="text-classification",
        model=_HF_OBJECTIVITY_MODEL_ID,
        tokenizer=_HF_OBJECTIVITY_MODEL_ID,
        device=-1,
        top_k=None,
    )
    return _objectivity_classifier


def _run_classifier_sync(text: str) -> tuple[float, float]:
    classifier = _load_classifier_sync()
    chunks = _chunk_text(text)
    raw = classifier(chunks, truncation=True, max_length=512)

    if raw and isinstance(raw[0], dict):
        raw = [raw]

    subj_scores: list[float] = []
    obj_scores: list[float] = []

    for batch in raw:
        row: dict[str, float] = {}
        for item in batch:
            label = str(item.get("label", "")).strip().lower().replace("_", "-")
            if label == "label-1":
                label = "biased"
            elif label == "label-0":
                label = "non-biased"
            row[label] = float(item.get("score", 0.0))

        subj = row.get("biased", 0.0)
        obj = row.get("non-biased", 0.0)
        if subj == 0.0 and obj > 0.0:
            subj = 1.0 - obj
        if obj == 0.0 and subj > 0.0:
            obj = 1.0 - subj
        total = subj + obj
        if total > 0:
            subj /= total
            obj /= total
        subj_scores.append(subj)
        obj_scores.append(obj)

    if not subj_scores:
        raise RuntimeError("Classifier returned no scores.")

    subj_prob = sum(subj_scores) / len(subj_scores)
    obj_prob = sum(obj_scores) / len(obj_scores)
    total = subj_prob + obj_prob
    if total > 0:
        subj_prob /= total
        obj_prob /= total
    else:
        subj_prob = 0.5
        obj_prob = 0.5

    return round(subj_prob, 4), round(obj_prob, 4)


def _fallback_notes(subjective_probability: float, is_subjective: bool) -> str:
    if is_subjective:
        return (
            f"This text appears to be primarily opinion-based "
            f"(subjectivity score: {subjective_probability:.0%}). "
            "It may reflect the author's perspective rather than neutral facts. "
            "Consider consulting additional sources for a balanced view."
        )
    return (
        f"This text appears to be primarily fact-based "
        f"(objectivity score: {1 - subjective_probability:.0%}). "
        "It presents information in a relatively neutral and balanced way."
    )


async def _generate_notes(text: str, subjective_probability: float, is_subjective: bool) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    print(api_key)
    if not api_key:
        return _fallback_notes(subjective_probability, is_subjective)

    label = "primarily subjective/opinion-based" if is_subjective else "primarily objective/fact-based"
    user_prompt = (
        f"Subjectivity probability: {subjective_probability:.1%} ({label}).\n\n"
        f"Text excerpt:\n{text[:4000]}\n\n"
        "In 2-3 plain sentences, explain whether this text is objective or subjective "
        "and what that means for the reader."
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
                        "You are a media literacy assistant. Write for a general audience. "
                        "Use plain language and a calm, informative tone."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except (AuthenticationError, RateLimitError, APIError, Exception) as exc:
        logger.warning("OpenAI objectivity notes failed (%s); using fallback.", exc)
        return _fallback_notes(subjective_probability, is_subjective)


async def detect_objectivity(text: str) -> ObjectivityAnalysisResult:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for objectivity analysis.")

    error: str | None = None
    subj_prob = 0.5
    obj_prob = 0.5

    try:
        loop = asyncio.get_event_loop()
        subj_prob, obj_prob = await loop.run_in_executor(None, _run_classifier_sync, text)
    except Exception as exc:
        logger.warning("Objectivity classifier failed (%s).", exc)
        error = str(exc)

    is_subjective = subj_prob >= _THRESHOLD
    notes = await _generate_notes(text, subj_prob, is_subjective)

    return ObjectivityAnalysisResult(
        subjective_probability=subj_prob,
        objective_probability=obj_prob,
        is_subjective=is_subjective,
        notes=notes,
        error=error,
    )
