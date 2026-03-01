import logging
import os

from openai import APIError, AsyncOpenAI, AuthenticationError, RateLimitError

from ..models.models import ScamAnalysisResult

logger = logging.getLogger(__name__)

_THRESHOLD = 0.5
_REVIEWER_MODEL = "gpt-4o-mini"

# Weighted signal categories — (keywords, weight)
_CATEGORIES: list[tuple[set[str], float]] = [
    # Urgency
    ({
        "urgent", "urgently", "immediately", "act now", "act fast",
        "limited time", "expires", "expiring", "deadline", "hurry",
        "respond now", "time sensitive", "time-sensitive", "last chance",
        "final notice", "final warning", "don't delay",
    }, 1.0),
    # Financial pressure
    ({
        "wire transfer", "bitcoin", "cryptocurrency", "crypto", "gift card",
        "money order", "western union", "moneygram", "routing number",
        "social security number", "tax refund", "unclaimed funds",
        "investment opportunity", "guaranteed return", "double your money",
    }, 2.0),
    # Threats / account actions
    ({
        "account suspended", "account locked", "account disabled",
        "account terminated", "verify your account", "confirm your account",
        "security alert", "security warning", "unauthorized access",
        "suspicious activity", "will be closed", "arrest warrant",
        "legal action", "law enforcement",
    }, 1.5),
    # Too-good-to-be-true
    ({
        "you've won", "you have won", "you are selected", "congratulations you",
        "lottery winner", "million dollar", "inheritance", "free money",
        "guaranteed income", "risk-free", "no cost to you", "make money fast",
        "work from home and earn",
    }, 2.0),
    # Impersonation signals
    ({
        "irs", "internal revenue service", "social security administration",
        "fbi", "federal bureau of investigation", "microsoft support",
        "apple support", "amazon support", "paypal support",
    }, 2.5),
    # Phishing actions
    ({
        "click here", "click the link", "click below",
        "download the attachment", "open the attachment",
        "provide your", "enter your password", "confirm your password",
        "update your billing", "update your payment", "verify your identity",
        "submit your information",
    }, 1.5),
]

_TOTAL_WEIGHT = sum(w for _, w in _CATEGORIES)


def _score(text: str) -> float:
    text_lower = text.lower()
    words = text.split()
    score = 0.0

    for signals, weight in _CATEGORIES:
        hits = sum(1 for s in signals if s in text_lower)
        score += min(hits / 3.0, 1.0) * weight

    # Excessive ALL-CAPS words (scam signal)
    if words:
        caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 2) / len(words)
        score += min(caps_ratio * 5, 1.0) * 0.5

    # Excessive exclamation marks
    exclaim_ratio = min(text.count("!") / max(len(words), 1) * 10, 1.0)
    score += exclaim_ratio * 0.5

    return round(min(score / (_TOTAL_WEIGHT + 1.0), 1.0), 4)


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
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for scam analysis.")

    scam_prob = _score(text)
    non_scam_prob = round(1.0 - scam_prob, 4)
    is_scam = scam_prob >= _THRESHOLD
    notes = await _generate_notes(text, scam_prob, is_scam)

    return ScamAnalysisResult(
        scam_probability=scam_prob,
        non_scam_probability=non_scam_prob,
        is_scam=is_scam,
        notes=notes,
        error=None,
    )
