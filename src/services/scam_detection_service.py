import json
import logging
from typing import Literal

import google.generativeai as genai

from ..config import settings
from ..models.scam_detection import ScamDetectionRequest, ScamDetectionResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Algorithmic detection
# ---------------------------------------------------------------------------

# Each entry: (keywords, reason_label, score_weight)
SCAM_SIGNALS: list[tuple[list[str], str, int]] = [
    (
        ["act now", "limited time", "expires today", "respond immediately", "urgent", "last chance"],
        "Urgency or pressure tactics",
        10,
    ),
    (
        ["wire transfer", "gift card", "bitcoin", "cryptocurrency", "money order", "western union", "send money"],
        "Unusual or untraceable payment method requested",
        20,
    ),
    (
        ["you've won", "you have won", "congratulations", "selected winner", "lottery", "prize claim", "unclaimed funds"],
        "Lottery, prize, or unexpected windfall claim",
        20,
    ),
    (
        ["legal action", "arrest warrant", "irs", "lawsuit", "police", "suspended", "account locked", "criminal charges"],
        "Threats of legal action or account suspension",
        25,
    ),
    (
        ["social security", "ssn", "bank account number", "routing number", "password", "credit card number", "pin number"],
        "Requests for sensitive personal or financial information",
        25,
    ),
    (
        ["guaranteed", "risk-free", "100% guaranteed", "double your money", "make money fast", "get rich", "no risk"],
        "Unrealistic financial promises",
        15,
    ),
    (
        ["click here", "verify now", "confirm your account", "update your information", "login to confirm"],
        "Phishing link or account verification pressure",
        15,
    ),
    (
        ["inheritance", "million dollars", "transfer funds", "next of kin", "foreign dignitary", "diplomat"],
        "Advance fee or inheritance fraud indicators",
        30,
    ),
    (
        ["work from home", "earn extra income", "passive income", "financial freedom", "easy money"],
        "Work-from-home or passive income scam signals",
        10,
    ),
    (
        ["you have been selected", "exclusive offer", "only you", "special chosen"],
        "Fake exclusivity or selection claims",
        10,
    ),
]


def _score_to_level(score: int) -> Literal["safe", "suspicious", "high_risk"]:
    if score <= 20:
        return "safe"
    if score <= 55:
        return "suspicious"
    return "high_risk"


def _algorithmic_detect(text: str) -> tuple[Literal["safe", "suspicious", "high_risk"], int, list[str]]:
    text_lower = text.lower()
    total_score = 0
    triggered_reasons: list[str] = []

    for keywords, reason, weight in SCAM_SIGNALS:
        if any(kw in text_lower for kw in keywords):
            total_score += weight
            triggered_reasons.append(reason)

    score = min(total_score, 100)
    level = _score_to_level(score)
    reasons = triggered_reasons if triggered_reasons else ["No common scam patterns detected"]

    return level, score, reasons


# ---------------------------------------------------------------------------
# Gemini detection
# ---------------------------------------------------------------------------

_GEMINI_PROMPT = """\
You are a scam detection expert. Analyze the following text and assess whether it is a scam.

Return a JSON object with exactly these fields:
- "level": one of "safe", "suspicious", or "high_risk"
- "score": integer 0–100 (0 = definitely safe, 100 = definite scam)
- "reasons": array of 1–5 concise strings explaining your assessment

Scoring guide:
- 0–20 → safe
- 21–55 → suspicious
- 56–100 → high_risk

Respond with only valid JSON. No markdown, no extra text.

Text to analyze:
\"\"\"
{text}
\"\"\"\
"""


async def _gemini_detect(text: str) -> tuple[Literal["safe", "suspicious", "high_risk"], int, list[str]]:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    response = await model.generate_content_async(_GEMINI_PROMPT.format(text=text))
    raw = response.text.strip()

    # Strip markdown code fences if Gemini adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)

    level = data["level"]
    if level not in ("safe", "suspicious", "high_risk"):
        raise ValueError(f"Unexpected level value: {level}")

    score = max(0, min(100, int(data["score"])))
    reasons = [str(r) for r in data["reasons"]]

    return level, score, reasons


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def detect_scam(request: ScamDetectionRequest) -> ScamDetectionResult:
    try:
        level, score, reasons = await _gemini_detect(request.input)
        return ScamDetectionResult(level=level, score=score, reasons=reasons, method="gemini")
    except Exception as exc:
        logger.warning("Gemini scam detection failed (%s), falling back to algorithmic.", exc)

    level, score, reasons = _algorithmic_detect(request.input)
    return ScamDetectionResult(level=level, score=score, reasons=reasons, method="algorithmic")
