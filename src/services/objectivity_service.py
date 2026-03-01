import logging
import os
import re

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..models.models import ObjectivityAnalysisResult

logger = logging.getLogger(__name__)

_THRESHOLD = 0.5
_REVIEWER_MODEL = "gpt-4o-mini"

_SUBJECTIVE_PHRASES = {
    "i think", "i believe", "i feel", "i consider", "i suppose",
    "in my opinion", "in my view", "personally", "from my perspective",
    "it seems to me", "as far as i'm concerned", "it seems like",
    "clearly", "obviously", "undoubtedly", "certainly", "it is clear that",
    "it is obvious that", "needless to say", "arguably", "perhaps",
    "maybe", "probably", "it appears that",
}

_OBJECTIVE_PHRASES = {
    "according to", "research shows", "studies show", "study found",
    "data indicates", "data shows", "evidence suggests", "evidence shows",
    "researchers found", "scientists found", "experts say", "experts found",
    "reported that", "published in", "peer-reviewed", "statistically",
    "the report states", "analysis shows", "measurements show",
    "survey found", "poll found", "census data",
}

_EMOTIONAL_WORDS = {
    "outrageous", "shocking", "horrifying", "disgusting", "appalling",
    "wonderful", "amazing", "fantastic", "incredible", "unbelievable",
    "terrible", "awful", "devastating", "catastrophic", "disastrous",
    "brilliant", "magnificent", "pathetic", "despicable", "monstrous",
    "glorious", "atrocious", "infuriating", "heartbreaking",
}

_FIRST_PERSON = {"i", "we", "my", "our", "me", "us", "myself", "ourselves"}


def _compute_subjectivity(text: str) -> float:
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)
    if not words:
        return 0.5

    word_count = len(words)

    subj_hits = sum(1 for p in _SUBJECTIVE_PHRASES if p in text_lower)
    obj_hits  = sum(1 for p in _OBJECTIVE_PHRASES  if p in text_lower)

    fp_density  = sum(1 for w in words if w in _FIRST_PERSON) / word_count
    emo_density = sum(1 for w in words if w in _EMOTIONAL_WORDS) / word_count

    # Weighted combination
    subj_score = (
        min(subj_hits / 5.0, 1.0)     * 0.35 +
        min(fp_density  * 20, 1.0)    * 0.30 +
        min(emo_density * 50, 1.0)    * 0.20 +
        max(0.0, 1.0 - min(obj_hits / 5.0, 1.0)) * 0.15
    )

    return round(min(max(subj_score, 0.0), 1.0), 4)


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

    subj_prob = _compute_subjectivity(text)
    obj_prob  = round(1.0 - subj_prob, 4)
    is_subjective = subj_prob >= _THRESHOLD
    notes = await _generate_notes(text, subj_prob, is_subjective)

    return ObjectivityAnalysisResult(
        subjective_probability=subj_prob,
        objective_probability=obj_prob,
        is_subjective=is_subjective,
        notes=notes,
        error=None,
    )
