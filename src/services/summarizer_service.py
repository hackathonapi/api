import logging
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIError

from ..config import settings

logger = logging.getLogger(__name__)



def _extractive_summarize(text: str, sentence_count: int) -> tuple[str | None, str | None]:
    """Fallback using sumy LexRank."""
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LexRankSummarizer()
        sentences = summarizer(parser.document, sentence_count)
        return " ".join(str(s) for s in sentences), None

    except Exception as exc:
        logger.warning("sumy fallback failed: %s", exc)
        return None, f"sumy error: {exc}"


async def summarize(text: str, sentence_count: int) -> tuple[str | None, str | None]:
    """
    Try OpenAI first; fall back to sumy LexRank if no key or on failure.
    Returns (summary, error_reason). summary is None only if both methods fail.
    """
    if settings.openai_api_key:
        try:
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
