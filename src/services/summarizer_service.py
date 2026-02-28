import asyncio
import logging
from typing import Literal

from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIError

from src.config import settings

logger = logging.getLogger(__name__)


# ---------- OpenAI ----------

async def _openai_summarize(text: str, sentence_count: int) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = (
        f"Summarize the following text in approximately {sentence_count} sentences. "
        f"Return only the summary, with no preamble.\n\n{text}"
    )
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


# ---------- sumy (sync, run in executor) ----------

def _sumy_summarize_sync(text: str, sentence_count: int) -> str:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lex_rank import LexRankSummarizer
    from sumy.nlp.stemmers import Stemmer
    from sumy.utils import get_stop_words

    language = "english"
    parser = PlaintextParser.from_string(text, Tokenizer(language))
    stemmer = Stemmer(language)
    summarizer = LexRankSummarizer(stemmer)
    summarizer.stop_words = get_stop_words(language)

    sentences = summarizer(parser.document, sentence_count)
    return " ".join(str(s) for s in sentences)


async def _sumy_summarize(text: str, sentence_count: int) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sumy_summarize_sync, text, sentence_count)


# ---------- Public interface ----------

async def summarize(
    text: str,
    method: Literal["openai", "sumy", "auto"],
    sentence_count: int,
) -> tuple[str, Literal["openai", "sumy"]]:
    """Returns (summary_text, method_actually_used)."""
    if method == "sumy":
        return await _sumy_summarize(text, sentence_count), "sumy"

    if method == "openai":
        return await _openai_summarize(text, sentence_count), "openai"

    # method == "auto": try OpenAI, fall back to sumy
    try:
        summary = await _openai_summarize(text, sentence_count)
        return summary, "openai"
    except (AuthenticationError, RateLimitError, APIError, ValueError) as exc:
        logger.warning("OpenAI summarization failed (%s), falling back to sumy.", exc)
        return await _sumy_summarize(text, sentence_count), "sumy"
