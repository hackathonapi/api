import asyncio
import logging
import re
from typing import Any

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..config import settings
from ..models.objectivity import ObjectivityAnalysisResult

_objectivity_classifier: Any = None
logger = logging.getLogger(__name__)


def _truncate_sentences(text: str, max_sentences: int = 4) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return " ".join(parts[:max_sentences])


def _chunk_text_for_classifier(text: str, max_chars: int = 2000) -> list[str]:
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


def _normalize_label(label: str) -> str:
    normalized = label.strip().lower().replace("_", "-")
    if normalized in {"biased", "non-biased"}:
        return normalized
    if normalized == "label-1":
        return "biased"
    if normalized == "label-0":
        return "non-biased"
    return normalized


def _load_objectivity_classifier_sync():
    global _objectivity_classifier
    if _objectivity_classifier is not None:
        return _objectivity_classifier

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ValueError(
            "transformers is required for objectivity classification. Install dependencies from requirements.txt."
        ) from exc

    _objectivity_classifier = pipeline(
        task="text-classification",
        model=settings.hf_objectivity_model_id,
        tokenizer=settings.hf_objectivity_model_id,
        device=-1,
        top_k=None,
    )
    return _objectivity_classifier


def _run_objectivity_classifier_sync(text: str) -> tuple[float, float, dict[str, float]]:
    classifier = _load_objectivity_classifier_sync()
    chunks = _chunk_text_for_classifier(text)
    raw_result = classifier(chunks, truncation=True, max_length=512)

    if raw_result and isinstance(raw_result[0], dict):
        raw_batches = [raw_result]
    else:
        raw_batches = raw_result

    subjective_scores: list[float] = []
    objective_scores: list[float] = []

    for batch in raw_batches:
        row_scores: dict[str, float] = {}
        for item in batch:
            label = _normalize_label(str(item.get("label", "")))
            score = float(item.get("score", 0.0))
            row_scores[label] = score

        # Common mappings:
        # - biased/non-biased models
        # - label_1/label_0 subjectivity models
        subjective = row_scores.get("biased", row_scores.get("label-1", 0.0))
        objective = row_scores.get("non-biased", row_scores.get("label-0", 0.0))

        if subjective == 0.0 and objective > 0.0:
            subjective = 1.0 - objective
        if objective == 0.0 and subjective > 0.0:
            objective = 1.0 - subjective

        total = subjective + objective
        if total > 0:
            subjective /= total
            objective /= total

        subjective_scores.append(subjective)
        objective_scores.append(objective)

    if not subjective_scores:
        raise RuntimeError("Classifier returned no scores.")

    subjective_probability = sum(subjective_scores) / len(subjective_scores)
    objective_probability = sum(objective_scores) / len(objective_scores)

    total = subjective_probability + objective_probability
    if total > 0:
        subjective_probability /= total
        objective_probability /= total
    else:
        subjective_probability = 0.5
        objective_probability = 0.5

    raw_scores = {
        "biased": round(subjective_probability, 4),
        "non-biased": round(objective_probability, 4),
    }
    return subjective_probability, objective_probability, raw_scores


def _fallback_objectivity_review(text: str, subjective_probability: float) -> str:
    preview = text.strip().replace("\n", " ")[:220]
    return (
        f"This text may be more opinion-based than fact-based (score {subjective_probability:.2f}). "
        "It may help to compare other trusted sources for a more balanced view. "
        f"Preview: {preview}"
    )


async def _generate_objectivity_review(text: str, subjective_probability: float) -> str:
    if not settings.openai_api_key:
        return _fallback_objectivity_review(text=text, subjective_probability=subjective_probability)

    prompt = (
        "Write a short note for a general reader, including older adults. "
        "Use plain words, short sentences, and a calm, respectful tone. "
        "Say the text may be subjective, and suggest checking other trusted sources for balance. "
        "Keep it to 3-4 sentences.\n\n"
        f"Subjective probability: {subjective_probability:.3f}\n\n"
        f"Text:\n{text[:5000]}"
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.objectivity_reviewer_model,
        temperature=0.2,
        max_tokens=220,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a media literacy assistant. Write for everyday readers, including older adults. "
                    "Use clear, simple language and a calm tone. Avoid jargon or loaded wording. "
                    "Suggest practical ways to check for a balanced perspective."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    text_out = (response.choices[0].message.content or "").strip()
    return _truncate_sentences(text_out, max_sentences=settings.objectivity_review_max_sentences)


async def detect_objectivity(
    text: str,
    threshold: float,
    review_with_llm: bool = True,
) -> ObjectivityAnalysisResult:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for objectivity analysis.")
    if not (0.0 <= threshold <= 1.0):
        raise ValueError("Threshold must be between 0 and 1.")

    loop = asyncio.get_event_loop()
    subjective_probability, objective_probability, raw_scores = await loop.run_in_executor(
        None, _run_objectivity_classifier_sync, text
    )

    is_subjective = subjective_probability >= threshold
    predicted_label = "SUBJECTIVE" if subjective_probability >= objective_probability else "OBJECTIVE"
    llm_review = None
    llm_review_model = None
    notes: str | None = None

    if is_subjective and review_with_llm:
        try:
            llm_review = await _generate_objectivity_review(
                text=text,
                subjective_probability=subjective_probability,
            )
            llm_review_model = (
                settings.objectivity_reviewer_model if settings.openai_api_key else "fallback-local"
            )
        except (AuthenticationError, RateLimitError, APIError, ValueError) as exc:
            logger.warning("OpenAI objectivity review failed (%s); using fallback review.", exc)
            llm_review = _fallback_objectivity_review(
                text=text,
                subjective_probability=subjective_probability,
            )
            llm_review_model = "fallback-local"
            notes = "OpenAI review failed; fallback review was used."

    return ObjectivityAnalysisResult(
        subjective_probability=round(subjective_probability, 4),
        objective_probability=round(objective_probability, 4),
        predicted_label=predicted_label,
        is_subjective=is_subjective,
        threshold=threshold,
        method_used="hf_subjectivity_classifier",
        raw_scores=raw_scores,
        llm_review=llm_review,
        llm_review_model=llm_review_model,
        notes=notes or (
            f"Model {settings.hf_objectivity_model_id}. "
            "label_1/biased is mapped to subjective; label_0/non-biased is mapped to objective."
        ),
    )
