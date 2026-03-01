"""
Unified analysis service — summarization, scam detection, objectivity, and bias
in a single module with one OpenAI call and pure-Python fallbacks.
"""
import heapq
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Thresholds & model
# ─────────────────────────────────────────────────────────────

_MODEL = "gpt-4o-mini"

# Backup-only: only conclude when score is clearly high/low.
# Anything between these triggers a "dubious" message.
_HIGH = 0.70
_LOW  = 0.20

# ─────────────────────────────────────────────────────────────
# Section tags (used in the OpenAI prompt and response parsing)
# ─────────────────────────────────────────────────────────────

_TAG_SUMMARY     = "=== SUMMARY ==="
_TAG_SCAM        = "=== SCAM ANALYSIS ==="
_TAG_OBJECTIVITY = "=== OBJECTIVITY ==="
_TAG_BIAS        = "=== BIAS ==="
_ALL_TAGS        = [_TAG_SUMMARY, _TAG_SCAM, _TAG_OBJECTIVITY, _TAG_BIAS]

_TAG_DISPLAY = {
    _TAG_SUMMARY:     "Summary",
    _TAG_SCAM:        "Scam Analysis",
    _TAG_OBJECTIVITY: "Objectivity",
    _TAG_BIAS:        "Bias",
}

# ─────────────────────────────────────────────────────────────
# Keyword lists
# ─────────────────────────────────────────────────────────────

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "it", "its", "this",
    "that", "these", "those", "i", "you", "he", "she", "we", "they",
    "not", "as", "if", "so", "than", "then", "when", "where", "which",
    "who", "what", "how", "all", "also", "just", "more", "their", "there",
}

_SCAM_CATEGORIES: list[tuple[set[str], float]] = [
    # Urgency
    ({"urgent", "urgently", "immediately", "act now", "act fast",
      "limited time", "expires", "expiring", "deadline", "hurry",
      "respond now", "time sensitive", "last chance",
      "final notice", "final warning"}, 1.0),
    # Financial pressure
    ({"wire transfer", "bitcoin", "cryptocurrency", "gift card",
      "money order", "western union", "routing number",
      "social security number", "tax refund", "unclaimed funds",
      "guaranteed return", "double your money"}, 2.0),
    # Threats / account actions
    ({"account suspended", "account locked", "account disabled",
      "verify your account", "security alert", "unauthorized access",
      "suspicious activity", "arrest warrant", "legal action"}, 1.5),
    # Too-good-to-be-true
    ({"you've won", "you have won", "lottery winner", "million dollar",
      "inheritance", "free money", "guaranteed income",
      "risk-free", "make money fast"}, 2.0),
    # Impersonation
    ({"irs", "internal revenue service", "social security administration",
      "fbi", "microsoft support", "apple support",
      "amazon support", "paypal support"}, 2.5),
    # Phishing actions
    ({"click here", "click the link", "download the attachment",
      "provide your", "enter your password", "update your billing",
      "verify your identity", "submit your information"}, 1.5),
]
_SCAM_TOTAL_WEIGHT = sum(w for _, w in _SCAM_CATEGORIES)

_SUBJECTIVE_PHRASES = {
    "i think", "i believe", "i feel", "i consider",
    "in my opinion", "in my view", "personally", "from my perspective",
    "it seems to me", "clearly", "obviously", "undoubtedly",
    "it is clear that", "arguably", "perhaps", "probably",
}
_OBJECTIVE_PHRASES = {
    "according to", "research shows", "studies show", "study found",
    "data indicates", "evidence suggests", "researchers found",
    "experts say", "reported that", "published in", "peer-reviewed",
    "analysis shows", "survey found", "census data",
}
_EMOTIONAL_WORDS = {
    "outrageous", "shocking", "horrifying", "disgusting", "appalling",
    "wonderful", "amazing", "fantastic", "incredible", "terrible",
    "awful", "devastating", "catastrophic", "brilliant", "pathetic",
    "despicable", "monstrous", "atrocious", "infuriating",
}
_FIRST_PERSON = {"i", "we", "my", "our", "me", "us", "myself"}

_BIAS_CATEGORIES: dict[str, set[str]] = {
    "political bias": {
        "radical", "extremist", "far-left", "far-right", "socialist",
        "fascist", "liberal agenda", "conservative agenda", "fake news",
        "deep state", "globalist", "nationalist", "communist", "marxist",
    },
    "emotional manipulation": {
        "must act now", "wake up", "they don't want you to know",
        "secret agenda", "exposing the truth", "think for yourself",
        "open your eyes", "the real truth", "hidden agenda",
    },
    "loaded language": {
        "regime", "invasion", "infested", "destroy", "eliminate",
        "eradicate", "thugs", "criminals", "radical agenda", "toxic",
        "epidemic", "catastrophe", "collapse", "meltdown",
    },
    "gender bias": {
        "women are", "men are", "like a woman", "like a man",
        "typical woman", "typical man", "women can't", "men can't",
        "women should", "men should stay",
    },
    "corporate bias": {
        "big pharma", "big tech", "corporate agenda", "wall street",
        "the elite", "the establishment", "follow the money",
        "funded by lobbyists",
    },
}
_BIAS_SATURATION = 3

# ─────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────

@dataclass
class AnalysisResult:
    summary:          Optional[str]    = None
    scam_notes:       Optional[str]    = None
    subjective_notes: Optional[str]    = None
    bias_notes:       Optional[str]    = None
    # AI-generated sections keyed by display name (for the PDF last page)
    ai_sections:      dict[str, str]   = field(default_factory=dict)

# ─────────────────────────────────────────────────────────────
# Heuristic scorers
# ─────────────────────────────────────────────────────────────

def _score_scam(text: str) -> float:
    text_lower = text.lower()
    words = text.split()
    score = 0.0
    for signals, weight in _SCAM_CATEGORIES:
        hits = sum(1 for s in signals if s in text_lower)
        score += min(hits / 3.0, 1.0) * weight
    if words:
        caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 2) / len(words)
        score += min(caps_ratio * 5, 1.0) * 0.5
    exclaim_ratio = min(text.count("!") / max(len(words), 1) * 10, 1.0)
    score += exclaim_ratio * 0.5
    return round(min(score / (_SCAM_TOTAL_WEIGHT + 1.0), 1.0), 4)


def _score_subjectivity(text: str) -> float:
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)
    if not words:
        return 0.5
    word_count = len(words)
    subj_hits  = sum(1 for p in _SUBJECTIVE_PHRASES if p in text_lower)
    obj_hits   = sum(1 for p in _OBJECTIVE_PHRASES  if p in text_lower)
    fp_density  = sum(1 for w in words if w in _FIRST_PERSON) / word_count
    emo_density = sum(1 for w in words if w in _EMOTIONAL_WORDS) / word_count
    subj_score = (
        min(subj_hits / 5.0, 1.0)              * 0.35 +
        min(fp_density * 20,  1.0)             * 0.30 +
        min(emo_density * 50, 1.0)             * 0.20 +
        max(0.0, 1.0 - min(obj_hits / 5.0, 1.0)) * 0.15
    )
    return round(min(max(subj_score, 0.0), 1.0), 4)


def _score_biases(text: str) -> dict[str, float]:
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)
    word_count = max(len(words), 1)
    scores: dict[str, float] = {}
    for category, signals in _BIAS_CATEGORIES.items():
        hits = sum(1 for s in signals if s in text_lower)
        length_factor = min(word_count / 200, 1.0)
        scores[category] = round(min(hits / _BIAS_SATURATION, 1.0) * length_factor, 4)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

# ─────────────────────────────────────────────────────────────
# Extractive summariser (fallback when OpenAI is unavailable)
# ─────────────────────────────────────────────────────────────

def _extractive_summarize(text: str, sentence_count: int) -> Optional[str]:
    try:
        raw: list[str] = []
        for line in re.split(r"\n+", text.strip()):
            raw.extend(re.split(r'(?<=[.!?])["\']?\s+(?=[A-Z"\'])', line))

        originals: list[str] = []
        sentences: list[str] = []
        for s in raw:
            s = s.strip()
            if len(s.split()) < 4:
                continue
            originals.append(s)
            sentences.append(s if re.search(r'[.!?]["\']?\s*$', s) else s + ".")

        if not sentences:
            return None

        words = re.findall(r"\b[a-z]+\b", text.lower())
        word_freq = Counter(w for w in words if w not in _STOP_WORDS)
        if not word_freq:
            return None

        max_freq = max(word_freq.values())
        normalized = {w: freq / max_freq for w, freq in word_freq.items()}
        scores = {
            sent: sum(normalized.get(w, 0) for w in re.findall(r"\b[a-z]+\b", sent.lower()))
            for sent in sentences
        }

        orig_by_display = dict(zip(sentences, originals))
        top = heapq.nlargest(sentence_count, scores, key=scores.get)
        top_ordered = sorted(top, key=lambda s: text.index(orig_by_display[s]))
        return " ".join(top_ordered)

    except Exception as exc:
        logger.warning("Extractive summarizer failed: %s", exc)
        return None

# ─────────────────────────────────────────────────────────────
# Backup messages (used when OpenAI does not respond)
# Only make a firm conclusion when the score is almost certain.
# In the middle, report "dubious".
# ─────────────────────────────────────────────────────────────

def _scam_backup(prob: float) -> str:
    if prob >= _HIGH:
        return (
            "This content shows clear signs of a scam attempt. "
            "Do not click links, share personal information, or make payments "
            "without verifying the source independently."
        )
    if prob <= _LOW:
        return "No significant scam signals were detected in this content."
    return (
        "OpenAI did not respond. Scam risk is dubious — "
        "treat this content with caution and verify before acting."
    )


def _objectivity_backup(prob: float) -> tuple[bool, str]:
    if prob >= _HIGH:
        return True, (
            "This text shows clear signs of being opinion-based rather than factual. "
            "Consider consulting additional sources for a balanced view."
        )
    if prob <= _LOW:
        return False, "This text appears largely objective and fact-based."
    return False, (
        "OpenAI did not respond. The objectivity of this content is dubious — "
        "seek multiple perspectives before drawing conclusions."
    )


def _bias_backup(scores: dict[str, float]) -> tuple[list[str], str]:
    clear_above = [k for k, v in scores.items() if v >= _HIGH]
    if clear_above:
        return clear_above, (
            f"Clear bias detected: {', '.join(clear_above)}. "
            "This content may present information in a one-sided way — "
            "seek additional sources."
        )
    if all(v <= _LOW for v in scores.values()):
        return [], "No significant bias patterns were detected in this content."
    return [], (
        "OpenAI did not respond. Bias level is dubious — "
        "seek additional perspectives before forming conclusions."
    )

# ─────────────────────────────────────────────────────────────
# OpenAI — single unified call
# ─────────────────────────────────────────────────────────────

def _parse_sections(raw: str) -> dict[str, str]:
    """Split OpenAI response by known section tags, return tag → content."""
    result: dict[str, str] = {}
    for i, tag in enumerate(_ALL_TAGS):
        start = raw.find(tag)
        if start == -1:
            continue
        content_start = start + len(tag)
        later = [
            raw.find(t, content_start)
            for t in _ALL_TAGS[i + 1:]
            if raw.find(t, content_start) != -1
        ]
        content_end = min(later) if later else len(raw)
        text = raw[content_start:content_end].strip()
        if text:
            result[tag] = text
    return result


async def _openai_analyze(
    text: str,
    sentence_count: int,
    scam_prob: float,
    subj_prob: float,
    biases_above_mid: list[str],
) -> dict[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {}

    bias_info = (
        f"Bias categories with some signal (score >= 0.5): {', '.join(biases_above_mid)}"
        if biases_above_mid
        else "No bias categories scored above 0.5."
    )

    prompt = (
        "Analyze the following text across four dimensions. "
        "Use the exact section headers shown. Write 2-3 plain sentences per section.\n\n"
        f"{_TAG_SUMMARY}\n"
        f"Summarize the text in approximately {sentence_count} sentences. Return only the summary.\n\n"
        f"{_TAG_SCAM}\n"
        f"Heuristic scam probability: {scam_prob:.1%}. "
        "Explain whether this content is safe or suspicious and what the reader should do.\n\n"
        f"{_TAG_OBJECTIVITY}\n"
        f"Heuristic subjectivity score: {subj_prob:.1%}. "
        "Explain whether this text is objective or subjective and what that means for the reader.\n\n"
        f"{_TAG_BIAS}\n"
        f"{bias_info}. "
        "Explain the bias patterns found (or their absence). "
        "Do NOT describe promotional tone or writing style — only confirmed bias types.\n\n"
        f"TEXT:\n{text[:5000]}"
    )

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=_MODEL,
            temperature=0.2,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a media literacy assistant. Write for a general audience. "
                        "Use plain language. Follow the section headers exactly as given."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        return _parse_sections(raw)
    except (AuthenticationError, RateLimitError, APIError, Exception) as exc:
        logger.warning("OpenAI unified analysis failed: %s", exc)
        return {}

# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

async def analyze(text: str, sentence_count: int) -> AnalysisResult:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for analysis.")
    sentence_count = max(1, min(sentence_count, 20))

    # ── 1. Heuristic scores (pure Python, no network) ──────────────────────
    scam_prob   = _score_scam(text)
    subj_prob   = _score_subjectivity(text)
    bias_scores = _score_biases(text)
    biases_above_mid = [k for k, v in bias_scores.items() if v >= 0.5]

    # ── 2. Single OpenAI call ───────────────────────────────────────────────
    ai = await _openai_analyze(text, sentence_count, scam_prob, subj_prob, biases_above_mid)

    # ── 3. Summary ──────────────────────────────────────────────────────────
    summary = ai.get(_TAG_SUMMARY) or _extractive_summarize(text, sentence_count)

    # ── 4. Scam notes ───────────────────────────────────────────────────────
    scam_notes = ai[_TAG_SCAM] if _TAG_SCAM in ai else _scam_backup(scam_prob)

    # ── 5. Objectivity notes ────────────────────────────────────────────────
    if _TAG_OBJECTIVITY in ai:
        subjective_notes = ai[_TAG_OBJECTIVITY]
    else:
        _, subjective_notes = _objectivity_backup(subj_prob)

    # ── 6. Bias notes ───────────────────────────────────────────────────────
    bias_notes = ai[_TAG_BIAS] if _TAG_BIAS in ai else _bias_backup(bias_scores)[1]

    # ── 7. AI sections for PDF last page (display name → text) ─────────────
    ai_sections = {
        _TAG_DISPLAY[tag]: text_
        for tag, text_ in ai.items()
        if tag in _TAG_DISPLAY
    }

    return AnalysisResult(
        summary=summary,
        scam_notes=scam_notes,
        subjective_notes=subjective_notes,
        bias_notes=bias_notes,
        ai_sections=ai_sections,
    )
