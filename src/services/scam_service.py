import asyncio
import logging
import re
from typing import Any

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..config import settings
from ..models.scam import ScamAnalysisResult

logger = logging.getLogger(__name__)

_scam_classifier: Any = None


def _truncate_sentences(text: str, max_sentences: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return " ".join(parts[:max_sentences])


def _chunk_text_for_classifier(text: str, max_chars: int = 1800) -> list[str]:
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


def _normalize_label(label: str) -> str:
    normalized = label.strip().upper().replace("_", "-")
    if normalized in {"SCAM", "NON-SCAM"}:
        return normalized
    if normalized == "LABEL-1":
        return "SCAM"
    if normalized == "LABEL-0":
        return "NON-SCAM"
    return normalized


def _load_scam_classifier_sync():
    global _scam_classifier
    if _scam_classifier is not None:
        return _scam_classifier

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ValueError(
            "transformers is required for scam classification. Install dependencies from requirements.txt."
        ) from exc

    _scam_classifier = pipeline(
        task="text-classification",
        model=settings.hf_scam_model_id,
        tokenizer=settings.hf_scam_model_id,
        device=-1,
        top_k=None,
    )
    return _scam_classifier


def _run_scam_classifier_sync(text: str) -> tuple[float, float, dict[str, float]]:
    classifier = _load_scam_classifier_sync()
    chunks = _chunk_text_for_classifier(text)
    raw_result = classifier(chunks, truncation=True, max_length=512)

    if raw_result and isinstance(raw_result[0], dict):
        raw_batches = [raw_result]
    else:
        raw_batches = raw_result

    scam_scores: list[float] = []
    non_scam_scores: list[float] = []

    for batch in raw_batches:
        row_scores: dict[str, float] = {}
        for item in batch:
            label = _normalize_label(str(item.get("label", "")))
            score = float(item.get("score", 0.0))
            row_scores[label] = score

        scam = row_scores.get("SCAM", row_scores.get("LABEL-1", 0.0))
        non_scam = row_scores.get("NON-SCAM", row_scores.get("LABEL-0", 0.0))

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

    scam_probability = sum(scam_scores) / len(scam_scores)
    non_scam_probability = sum(non_scam_scores) / len(non_scam_scores)

    total = scam_probability + non_scam_probability
    if total > 0:
        scam_probability /= total
        non_scam_probability /= total
    else:
        scam_probability = 0.5
        non_scam_probability = 0.5

    raw_scores = {
        "SCAM": round(scam_probability, 4),
        "NON-SCAM": round(non_scam_probability, 4),
    }
    return scam_probability, non_scam_probability, raw_scores


def _fallback_review(text: str, scam_probability: float) -> str:
    preview = text.strip().replace("\n", " ")[:180]
    return (
        f"This message may be a scam or phishing attempt (score {scam_probability:.2f}). "
        "Please double-check with a trusted source before you click, pay, or reply. "
        f"Preview: {preview}"
    )


async def _generate_openai_review(text: str, scam_probability: float) -> str:
    if not settings.openai_api_key:
        return _fallback_review(text=text, scam_probability=scam_probability)

    prompt = (
        "Write a short safety note for a general reader, including older adults. "
        "Use plain words, short sentences, and a calm, respectful tone. "
        "Say the message may be a scam or phishing attempt, and give simple safe next steps. "
        "Keep it to 3-4 sentences.\n\n"
        f"Classifier scam probability: {scam_probability:.3f}\n\n"
        f"Message:\n{text[:5000]}"
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.scam_reviewer_model,
        temperature=0.2,
        max_tokens=220,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a security assistant for scam/phishing analysis. Write for everyday readers, "
                    "including older adults. Use clear, simple language and practical advice. "
                    "Avoid jargon, blame, and alarmist wording."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    text_out = (response.choices[0].message.content or "").strip()
    return _truncate_sentences(text_out, max_sentences=settings.scam_review_max_sentences)


async def detect_scam(
    text: str,
    threshold: float,
    review_with_llm: bool = True,
) -> ScamAnalysisResult:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for scam analysis.")

    if not (0.0 <= threshold <= 1.0):
        raise ValueError("Threshold must be between 0 and 1.")

    loop = asyncio.get_event_loop()
    scam_prob, non_scam_prob, raw_scores = await loop.run_in_executor(
        None, _run_scam_classifier_sync, text
    )

    is_scam = scam_prob >= threshold
    predicted_label = "SCAM" if scam_prob >= non_scam_prob else "NON-SCAM"

    llm_review = None
    llm_review_model = None
    notes = None

    if is_scam and review_with_llm:
        try:
            llm_review = await _generate_openai_review(text=text, scam_probability=scam_prob)
            llm_review_model = settings.scam_reviewer_model if settings.openai_api_key else "fallback-local"
        except (AuthenticationError, RateLimitError, APIError, ValueError) as exc:
            logger.warning("OpenAI scam review failed (%s); using fallback review text.", exc)
            llm_review = _fallback_review(text=text, scam_probability=scam_prob)
            llm_review_model = "fallback-local"
            notes = "OpenAI review failed; fallback review was used."

    return ScamAnalysisResult(
        scam_probability=round(scam_prob, 4),
        non_scam_probability=round(non_scam_prob, 4),
        predicted_label=predicted_label,
        is_scam=is_scam,
        threshold=threshold,
        method_used="hf_bert_scam_classifier_v1_6",
        raw_scores=raw_scores,
        llm_review=llm_review,
        llm_review_model=llm_review_model,
        notes=notes,
    )
