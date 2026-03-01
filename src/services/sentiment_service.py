import asyncio
import logging
import re
from typing import Any, Literal

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..config import settings
from ..models.sentiment import BiasSignals, SentimentAnalysisResult

logger = logging.getLogger(__name__)


POSITIVE_WORDS = {
    "good", "great", "excellent", "beneficial", "accessible", "fair",
    "improve", "positive", "helpful", "effective", "support",
}

NEGATIVE_WORDS = {
    "bad", "poor", "harmful", "biased", "unfair", "inaccessible",
    "worse", "negative", "problem", "broken", "fail", "failing",
}

LOADED_WORDS = {
    "obviously", "clearly", "outrageous", "shocking", "disgraceful",
    "ridiculous", "undeniable", "propaganda",
}

ABSOLUTIST_WORDS = {
    "always", "never", "everyone", "nobody", "all", "none", "must",
}

FIRST_PERSON_WORDS = {"i", "me", "my", "mine", "we", "our", "us"}

_bias_classifier: Any = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _count_hits(tokens: list[str], lexicon: set[str]) -> int:
    return sum(1 for token in tokens if token in lexicon)


def _bound_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _truncate_sentences(text: str, max_sentences: int = 4) -> str:
    if not text.strip():
        return text

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return " ".join(parts[:max_sentences])


def _chunk_text_for_classifier(text: str, max_chars: int = 2500) -> list[str]:
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


def _load_bias_classifier_sync():
    global _bias_classifier
    if _bias_classifier is not None:
        return _bias_classifier

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ValueError(
            "transformers is required for hf_modernbert_bias. Install dependencies from requirements.txt."
        ) from exc

    _bias_classifier = pipeline(
        task="text-classification",
        model=settings.hf_bias_model_id,
        tokenizer=settings.hf_bias_model_id,
        device=-1,
        top_k=None,
    )
    return _bias_classifier


def _normalize_label(label: str) -> str:
    return label.strip().lower().replace("_", " ")


def _run_bias_classifier_sync(text: str) -> dict[str, float]:
    classifier = _load_bias_classifier_sync()
    chunks = _chunk_text_for_classifier(text)

    # With top_k=None, HF returns all labels per text:
    # list[dict] for single input or list[list[dict]] for multi-input.
    raw_result = classifier(chunks, truncation=True, max_length=512)

    if raw_result and isinstance(raw_result, list) and raw_result and isinstance(raw_result[0], dict):
        raw_batches = [raw_result]
    else:
        raw_batches = raw_result

    scores: dict[str, float] = {}
    for batch in raw_batches:
        for item in batch:
            label = _normalize_label(str(item.get("label", "")))
            score = float(item.get("score", 0.0))
            if not label:
                continue
            scores[label] = max(scores.get(label, 0.0), score)

    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {label: round(score, 4) for label, score in sorted_items}


def _fallback_bias_explanation(text: str, selected_biases: dict[str, float], cutoff: float) -> str:
    if not selected_biases:
        return (
            f"No bias type scored above the cutoff of {cutoff:.2f}. "
            "This text looks mostly neutral in this check."
        )

    top_biases = ", ".join(
        f"{label} ({score:.2f})" for label, score in list(selected_biases.items())[:3]
    )
    summary = (
        f"This check found possible {top_biases} bias patterns in the text. "
        "Some wording may present people or viewpoints in an uneven way. "
        "Read carefully and consider whether a more balanced point of view is possible."
    )
    return _truncate_sentences(summary, max_sentences=4)


async def _generate_bias_explanation(text: str, selected_biases: dict[str, float], cutoff: float) -> str:
    if not settings.openai_api_key:
        return _fallback_bias_explanation(text=text, selected_biases=selected_biases, cutoff=cutoff)

    bias_string = ", ".join(f"{k}: {v:.3f}" for k, v in selected_biases.items()) or "none above cutoff"
    clipped_text = text[:6000]

    prompt = (
        "Write a short note for a general reader, including older adults. "
        "Use plain words, short sentences, and a calm, respectful tone. "
        "Say the text may be biased, and be specific about how. "
        "Name the likely bias type explicitly (for example, islamophobia, antisemitism, racism, sexism, xenophobia) "
        "when the wording supports it. "
        "Explain which part of the text shows the bias and what stereotype or assumption it relies on. "
        "If relevant, you may briefly mention common historical context that can fuel prejudice "
        "(for example, post-9/11 anti-Muslim stereotypes), but do not speculate about the author's intent. "
        "Do not use generic filler like 'consider balanced information' unless you first provide concrete analysis. "
        "Keep it to 3-4 sentences.\n\n"
        f"Biases (score >= {cutoff:.2f}): {bias_string}\n\n"
        f"Text:\n{clipped_text}"
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.bias_explainer_model,
        temperature=0.2,
        max_tokens=220,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a bias analysis assistant. Write for everyday readers, including older adults. "
                    "Use clear, simple language. Avoid jargon, blame, and alarmist wording. "
                    "Present findings as possible bias signals. Be concrete and text-grounded: "
                    "name the specific bias category when supported, cite the problematic framing, "
                    "and explain why it is harmful or misleading."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    generated = (response.choices[0].message.content or "").strip()
    return _truncate_sentences(generated, max_sentences=settings.bias_explanation_max_sentences)


def _rule_based_metrics(text: str) -> tuple[Literal["positive", "negative", "neutral", "mixed"], float, float, BiasSignals]:
    tokens = _tokenize(text)
    if not tokens:
        raise ValueError("Text cannot be empty for sentiment analysis.")

    token_count = len(tokens)
    positive_hits = _count_hits(tokens, POSITIVE_WORDS)
    negative_hits = _count_hits(tokens, NEGATIVE_WORDS)
    loaded_hits = _count_hits(tokens, LOADED_WORDS)
    absolutist_hits = _count_hits(tokens, ABSOLUTIST_WORDS)
    first_person_hits = _count_hits(tokens, FIRST_PERSON_WORDS)

    sentiment_score = 0.0
    if positive_hits or negative_hits:
        sentiment_score = (positive_hits - negative_hits) / max((positive_hits + negative_hits), 1)
    sentiment_score = _bound_float(sentiment_score, -1.0, 1.0)

    if positive_hits > 0 and negative_hits > 0 and abs(sentiment_score) <= 0.2:
        tone: Literal["positive", "negative", "neutral", "mixed"] = "mixed"
    elif sentiment_score >= 0.2:
        tone = "positive"
    elif sentiment_score <= -0.2:
        tone = "negative"
    else:
        tone = "neutral"

    subjectivity_score = (
        loaded_hits + absolutist_hits + first_person_hits + positive_hits + negative_hits
    ) / max(token_count, 1)
    subjectivity_score = _bound_float(subjectivity_score, 0.0, 1.0)

    confidence = 0.45 + min(abs(sentiment_score), 0.5)
    confidence = _bound_float(confidence, 0.0, 0.95)

    signals = BiasSignals(
        loaded_language_hits=loaded_hits,
        absolutist_language_hits=absolutist_hits,
        first_person_hits=first_person_hits,
        subjectivity_score=round(subjectivity_score, 4),
    )

    return tone, round(sentiment_score, 4), round(confidence, 4), signals


async def _rule_based_analyze(text: str, bias_cutoff: float) -> SentimentAnalysisResult:
    tone, sentiment_score, confidence, signals = _rule_based_metrics(text)
    subjectivity_score = signals.subjectivity_score

    if subjectivity_score >= 0.12:
        bias_risk: Literal["low", "medium", "high"] = "high"
    elif subjectivity_score >= 0.06:
        bias_risk = "medium"
    else:
        bias_risk = "low"

    explanation = _fallback_bias_explanation(text=text, selected_biases={}, cutoff=bias_cutoff)
    return SentimentAnalysisResult(
        tone=tone,
        bias_risk=bias_risk,
        sentiment_score=sentiment_score,
        confidence=confidence,
        method_used="rule_based",
        bias_cutoff=bias_cutoff,
        bias_scores={},
        biases_above_cutoff=[],
        bias_explanation=explanation,
        signals=signals,
        notes="Rule-based fallback; no transformer bias model used.",
    )


async def _hf_modernbert_bias_analyze(text: str, bias_cutoff: float) -> SentimentAnalysisResult:
    tone, sentiment_score, baseline_confidence, signals = _rule_based_metrics(text)
    loop = asyncio.get_event_loop()
    bias_scores = await loop.run_in_executor(None, _run_bias_classifier_sync, text)

    selected_biases = {k: v for k, v in bias_scores.items() if v >= bias_cutoff}
    max_score = max(bias_scores.values()) if bias_scores else 0.0

    if max_score >= 0.85:
        bias_risk: Literal["low", "medium", "high"] = "high"
    elif max_score >= bias_cutoff:
        bias_risk = "medium"
    else:
        bias_risk = "low"

    explanation = await _generate_bias_explanation(
        text=text,
        selected_biases=selected_biases,
        cutoff=bias_cutoff,
    )

    confidence = _bound_float(max(max_score, baseline_confidence), 0.0, 1.0)
    return SentimentAnalysisResult(
        tone=tone,
        bias_risk=bias_risk,
        sentiment_score=sentiment_score,
        confidence=round(confidence, 4),
        method_used="hf_modernbert_bias",
        bias_cutoff=bias_cutoff,
        bias_scores=bias_scores,
        biases_above_cutoff=list(selected_biases.keys()),
        bias_explanation=explanation,
        signals=signals,
        notes=(
            f"Bias model: {settings.hf_bias_model_id}. "
            f"Selected biases are scores >= {bias_cutoff:.2f}."
        ),
    )


async def analyze_sentiment(
    text: str,
    method: Literal["hf_modernbert_bias", "rule_based", "auto"],
    bias_cutoff: float,
) -> SentimentAnalysisResult:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for sentiment analysis.")

    if method == "rule_based":
        return await _rule_based_analyze(text=text, bias_cutoff=bias_cutoff)

    if method == "hf_modernbert_bias":
        return await _hf_modernbert_bias_analyze(text=text, bias_cutoff=bias_cutoff)

    # method == "auto": try transformer path, then fall back to rule-based
    try:
        return await _hf_modernbert_bias_analyze(text=text, bias_cutoff=bias_cutoff)
    except (ValueError, RuntimeError, ImportError, AuthenticationError, RateLimitError, APIError) as exc:
        logger.warning("hf_modernbert_bias failed (%s), falling back to rule-based.", exc)
        return await _rule_based_analyze(text=text, bias_cutoff=bias_cutoff)
