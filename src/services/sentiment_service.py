import asyncio
import logging
import os
import re
from typing import Any

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..models.models import SentimentAnalysisResult

logger = logging.getLogger(__name__)

_HF_BIAS_MODEL_ID = "cirimus/modernbert-large-bias-type-classifier"
_BIAS_CUTOFF = 0.7
_EXPLAINER_MODEL = "gpt-4o-mini"

_bias_classifier: Any = None


def _chunk_text(text: str, max_chars: int = 2500) -> list[str]:
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
    global _bias_classifier
    if _bias_classifier is not None:
        return _bias_classifier
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ValueError("transformers is required. Install dependencies from requirements.txt.") from exc
    _bias_classifier = pipeline(
        task="text-classification",
        model=_HF_BIAS_MODEL_ID,
        tokenizer=_HF_BIAS_MODEL_ID,
        device=-1,
        top_k=None,
    )
    return _bias_classifier


def _run_classifier_sync(text: str) -> dict[str, float]:
    classifier = _load_classifier_sync()
    chunks = _chunk_text(text)
    raw = classifier(chunks, truncation=True, max_length=512)

    if raw and isinstance(raw[0], dict):
        raw = [raw]

    scores: dict[str, float] = {}
    for batch in raw:
        for item in batch:
            label = str(item.get("label", "")).strip().lower().replace("_", " ")
            score = float(item.get("score", 0.0))
            if label:
                scores[label] = max(scores.get(label, 0.0), score)

    return {k: round(v, 4) for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)}


def _fallback_notes(biases_above_cutoff: list[str]) -> str:
    if not biases_above_cutoff:
        return (
            "No significant bias patterns were detected in this text. "
            "The content appears to present information in a relatively balanced way."
        )
    bias_list = ", ".join(biases_above_cutoff[:3])
    return (
        f"This text shows signs of the following bias types: {bias_list}. "
        "Some wording may present people or viewpoints in an uneven or one-sided way. "
        "Consider seeking additional sources for a more balanced perspective."
    )


async def _generate_notes(text: str, biases_above_cutoff: list[str]) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _fallback_notes(biases_above_cutoff)

    if biases_above_cutoff:
        bias_list = ", ".join(biases_above_cutoff)
        user_prompt = (
            f"Bias types detected (score >= {_BIAS_CUTOFF}): {bias_list}.\n\n"
            f"Text excerpt:\n{text[:4000]}\n\n"
            "In 2-3 plain sentences, explain what specific bias patterns appear in this text "
            "and why a reader should be aware of them."
        )
    else:
        user_prompt = (
            f"No bias types scored above {_BIAS_CUTOFF}.\n\n"
            f"Text excerpt:\n{text[:4000]}\n\n"
            "In 1-2 plain sentences, confirm that no significant bias was detected."
        )

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=_EXPLAINER_MODEL,
            temperature=0.2,
            max_tokens=180,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a bias analysis assistant. Write for a general audience. "
                        "Use plain language. Be concise, specific, and non-alarmist."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except (AuthenticationError, RateLimitError, APIError, Exception) as exc:
        logger.warning("OpenAI bias notes failed (%s); using fallback.", exc)
        return _fallback_notes(biases_above_cutoff)


async def analyze_sentiment(text: str) -> SentimentAnalysisResult:
    # TEMPORARILY DISABLED — models removed for deployment testing
    return SentimentAnalysisResult(
        bias_cutoff=_BIAS_CUTOFF,
        bias_scores={},
        biases_above_cutoff=[],
        notes="Bias analysis temporarily disabled.",
        error=None,
    )
