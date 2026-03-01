import logging
import os
import re

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..models.models import SentimentAnalysisResult

logger = logging.getLogger(__name__)

_BIAS_CUTOFF = 0.5
_EXPLAINER_MODEL = "gpt-4o-mini"

# Each category maps to a set of signal phrases and a normalisation cap
_BIAS_CATEGORIES: dict[str, set[str]] = {
    "political bias": {
        "radical", "extremist", "far-left", "far-right", "socialist", "fascist",
        "liberal agenda", "conservative agenda", "fake news", "mainstream media",
        "deep state", "globalist", "nationalist", "communist", "marxist",
        "left-wing propaganda", "right-wing propaganda", "biased media",
    },
    "emotional manipulation": {
        "must act now", "wake up", "they don't want you to know",
        "what they're hiding", "secret agenda", "exposing the truth",
        "think for yourself", "open your eyes", "the real truth",
        "you won't believe", "shocking revelation", "hidden agenda",
    },
    "loaded language": {
        "regime", "invasion", "plague", "epidemic of", "infested",
        "destroy", "eliminate", "eradicate", "thugs", "criminals",
        "radical agenda", "toxic", "poison", "epidemic", "crisis",
        "catastrophe", "collapse", "meltdown", "rampage",
    },
    "gender bias": {
        "women are", "men are", "females are", "males are",
        "like a woman", "like a man", "typical woman", "typical man",
        "women can't", "men can't", "women don't", "men don't",
        "women should", "men should stay",
    },
    "corporate bias": {
        "big pharma", "big tech", "mainstream media", "corporate agenda",
        "wall street", "the elite", "the establishment", "corporate overlords",
        "follow the money", "paid by", "funded by lobbyists",
    },
}

# How many hits (per category) to reach a score of 1.0
_SATURATION = 3


def _score_categories(text: str) -> dict[str, float]:
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)
    word_count = max(len(words), 1)

    scores: dict[str, float] = {}
    for category, signals in _BIAS_CATEGORIES.items():
        hits = sum(1 for s in signals if s in text_lower)
        # Normalise: _SATURATION hits → score of 1.0; scale by text length so
        # short texts aren't unfairly penalised
        length_factor = min(word_count / 200, 1.0)  # generous for short texts
        raw = min(hits / _SATURATION, 1.0) * length_factor
        scores[category] = round(raw, 4)

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


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
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for sentiment analysis.")

    bias_scores = _score_categories(text)
    biases_above_cutoff = [k for k, v in bias_scores.items() if v >= _BIAS_CUTOFF]
    notes = await _generate_notes(text, biases_above_cutoff)

    return SentimentAnalysisResult(
        bias_cutoff=_BIAS_CUTOFF,
        bias_scores=bias_scores,
        biases_above_cutoff=biases_above_cutoff,
        notes=notes,
        error=None,
    )
