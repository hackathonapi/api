import heapq
import logging
import re
import os
from collections import Counter

from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIError

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "it", "its", "this",
    "that", "these", "those", "i", "you", "he", "she", "we", "they",
    "not", "as", "if", "so", "than", "then", "when", "where", "which",
    "who", "what", "how", "all", "also", "just", "more", "their", "there",
}


def _extractive_summarize(text: str, sentence_count: int) -> tuple[str | None, str | None]:
    """Pure-Python fallback: word frequency + sentence scoring, no dependencies."""
    try:
        raw: list[str] = []
        for line in re.split(r"\n+", text.strip()):
            raw.extend(re.split(r'(?<=[.!?])["\']?\s+(?=[A-Z"\'])', line))

        sentences = []
        for s in raw:
            s = s.strip()
            if len(s.split()) < 4:
                continue
            if not re.search(r'[.!?]["\']?\s*$', s):
                s = s.rstrip() + "."
            sentences.append(s)

        if not sentences:
            return None, "could not split text into sentences"

        words = re.findall(r"\b[a-z]+\b", text.lower())
        word_freq = Counter(w for w in words if w not in _STOP_WORDS)

        if not word_freq:
            return None, "no meaningful words found"

        max_freq = max(word_freq.values())
        normalized = {w: freq / max_freq for w, freq in word_freq.items()}

        scores = {
            sent: sum(normalized.get(w, 0) for w in re.findall(r"\b[a-z]+\b", sent.lower()))
            for sent in sentences
        }

        top = heapq.nlargest(sentence_count, scores, key=scores.get)
        top_ordered = sorted(top, key=lambda s: text.index(s))
        return " ".join(top_ordered), None

    except Exception as exc:
        logger.warning("Extractive fallback failed: %s", exc)
        return None, f"extractive error: {exc}"


async def summarize(text: str, sentence_count: int) -> tuple[str | None, str | None]:
    """
    Try OpenAI first; fall back to pure-Python extractive summarization.
    Returns (summary, error_reason). summary is None only if both methods fail.
    """
    if os.environ.get('OPENAI_API_KEY'):
        try:
            client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            prompt = (
                f"Summarize the following text in approximately {sentence_count} sentences. "
                f"Return only the summary, with no preamble.\n\n{text}"
            )
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip(), None
        except AuthenticationError:
            logger.warning("OpenAI summarization failed: invalid API key")
            openai_error = "invalid OpenAI API key"
        except RateLimitError:
            logger.warning("OpenAI summarization failed: rate limit exceeded")
            openai_error = "OpenAI rate limit exceeded"
        except (APIError, ValueError) as exc:
            logger.warning("OpenAI summarization failed: %s", exc)
            openai_error = f"OpenAI error: {exc}"
    else:
        openai_error = "no OpenAI API key configured"

    summary, extractive_error = _extractive_summarize(text, sentence_count)
    if summary is not None:
        return summary, None

    return None, f"{openai_error}; {extractive_error}"