# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import asyncio
import os
import re
import tempfile
from typing import Optional
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs

import httpx
import pymupdf
from newspaper import Article, Config
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    input: str


class ExtractionResult(BaseModel):
    content: str
    input_type: str
    source: str
    word_count: int
    extraction_method: str
    error: Optional[str]


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", " ")
    text = re.sub(r" {2,}", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Paywall detection
# ---------------------------------------------------------------------------

class PaywallDetected(Exception):
    pass


KNOWN_PAYWALL_DOMAINS = {
    "nytimes.com", "wsj.com", "ft.com", "bloomberg.com",
    "economist.com", "thetimes.co.uk", "theatlantic.com",
    "newyorker.com", "wired.com", "hbr.org", "foreignpolicy.com",
    "statista.com", "businessinsider.com",
}

PAYWALL_SIGNALS = [
    "subscribe to continue reading",
    "subscribe to read",
    "sign in to read",
    "create a free account to continue",
    "you've reached your free article limit",
    "this article is for subscribers only",
    "subscribers only",
    "unlock this article",
    "get full access",
    "join to read more",
    "register to continue",
    "premium content",
    "become a member to read",
]


def check_for_paywall(url: str, html: str, word_count: int):
    domain = urlparse(url).netloc.lower().replace("www.", "")

    if any(domain.endswith(d) for d in KNOWN_PAYWALL_DOMAINS):
        raise PaywallDetected(
            f"'{domain}' is a known paywalled publication. "
            "Please access the content directly and paste the text as input instead."
        )

    html_lower = html.lower()
    for signal in PAYWALL_SIGNALS:
        if signal in html_lower:
            raise PaywallDetected(
                "This content appears to be behind a paywall. "
                "Please paste the text directly as input instead."
            )

    if word_count < 120:
        raise PaywallDetected(
            "This page returned very little text and may be paywalled or require login. "
            "Please paste the text directly as input instead."
        )


# ---------------------------------------------------------------------------
# URL detection
# ---------------------------------------------------------------------------

def _is_url(text: str) -> bool:
    text = text.strip()
    if re.match(r'^https?://', text):
        return True
    # No spaces + looks like a domain (e.g. "example.com/path")
    if ' ' not in text and re.match(r'^[\w.-]+\.[a-zA-Z]{2,}', text):
        return True
    return False


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------

def clean_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    tracking_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term",
        "utm_content", "fbclid", "gclid", "ref", "source",
        "mc_cid", "mc_eid", "igshid", "si", "feature",
    }

    query_params = parse_qs(parsed.query)
    cleaned_params = {
        k: v for k, v in query_params.items()
        if k.lower() not in tracking_params
    }

    cleaned = parsed._replace(query=urlencode(cleaned_params, doseq=True))
    return urlunparse(cleaned)


def detect_url_type(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.lower()
    
    if domain in ("reddit.com", "old.reddit.com", "new.reddit.com"):
        return "reddit"

    if path.endswith(".pdf"):
        return "pdf_url"

    return "generic"


# ---------------------------------------------------------------------------
# Generic scraping helpers
# ---------------------------------------------------------------------------

def _newspaper_config() -> Config:
    config = Config()
    config.browser_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
    config.request_timeout = 15
    config.fetch_images = False
    return config


def _run_newspaper(url: str, input_html: Optional[str] = None) -> tuple[str, str, str]:
    """Download and parse an article with newspaper. Returns (raw_html, title, text).
    Synchronous — always call via asyncio.to_thread."""
    article = Article(url, config=_newspaper_config())
    if input_html:
        article.download(input_html=input_html)
    else:
        article.download()
    article.parse()
    return article.html, article.title or "", article.text or ""


def _get_playwright_html(url: str) -> Optional[str]:
    """Render a JS-heavy page with Playwright and return the full HTML."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Block images/fonts/css — we only need the DOM text
            page.route(
                "**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}",
                lambda route: route.abort(),
            )

            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
            return html

    except Exception:
        return None


# ---------------------------------------------------------------------------
# URL extractors
# ---------------------------------------------------------------------------


async def extract_reddit(url: str) -> ExtractionResult:
    url = url.replace("www.reddit.com", "old.reddit.com")
    url = url.replace("new.reddit.com", "old.reddit.com")

    headers = {"User-Agent": "Mozilla/5.0 (compatible; accessibility-api/1.0)"}

    try:
        # Reddit exposes .json on any post URL — simpler than scraping HTML
        json_url = url.rstrip("/") + ".json"

        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.get(json_url, headers=headers)
            response.raise_for_status()
            data = response.json()

        post = data[0]["data"]["children"][0]["data"]
        title = post.get("title", "").strip()
        body = post.get("selftext", "").strip()

        if body in ("", "[deleted]", "[removed]"):
            body = ""

        content = _normalize(f"{title}\n\n{body}")

        if not content:
            return ExtractionResult(
                content="", source=url, input_type="url",
                word_count=0, extraction_method="reddit_json",
                error="Post appears to be empty, deleted, or a link post with no body.",
            )

        return ExtractionResult(
            content=content, source=url, input_type="url",
            word_count=len(content.split()),
            extraction_method="reddit_json", error=None,
        )

    except Exception as e:
        return ExtractionResult(
            content="", source=url, input_type="url",
            word_count=0, extraction_method="reddit_json",
            error=f"Could not extract Reddit post: {str(e)}",
        )


async def extract_pdf_url(url: str) -> ExtractionResult:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

        # PyMuPDF requires a file path, so buffer to a temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        try:
            doc = pymupdf.open(tmp_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
        finally:
            os.unlink(tmp_path)

        text = _normalize(text)

        if not text:
            return ExtractionResult(
                content="", source=url, input_type="url",
                word_count=0, extraction_method="pdf_url",
                error="PDF contains no extractable text. It may be a scanned image PDF.",
            )

        return ExtractionResult(
            content=text, source=url, input_type="url",
            word_count=len(text.split()),
            extraction_method="pdf_url", error=None,
        )

    except Exception as e:
        return ExtractionResult(
            content="", source=url, input_type="url",
            word_count=0, extraction_method="pdf_url",
            error=f"Could not download or extract PDF: {str(e)}",
        )


async def extract_generic(url: str) -> ExtractionResult:
    method = "newspaper"
    content = None

    # Check known paywall domains before attempting any download
    domain = urlparse(url).netloc.lower().replace("www.", "")
    if any(domain.endswith(d) for d in KNOWN_PAYWALL_DOMAINS):
        return ExtractionResult(
            content="", source=url, input_type="url",
            word_count=0, extraction_method="newspaper",
            error=(
                f"'{domain}' is a known paywalled publication. "
                "Please access the content directly and paste the text as input instead."
            ),
        )

    # Tier 1: newspaper — handles most static pages
    try:
        raw_html, title, text = await asyncio.to_thread(_run_newspaper, url)
        # Check for soft paywalls using HTML signals and word count
        check_for_paywall(url, raw_html, len(raw_html.split()))
        content = _normalize(f"{title}\n\n{text}" if title else text)
    except PaywallDetected as e:
        return ExtractionResult(
            content="", source=url, input_type="url",
            word_count=0, extraction_method="newspaper",
            error=str(e),
        )
    except Exception:
        content = None

    # Tier 2: Playwright fallback for JS-heavy pages — feeds rendered HTML back into newspaper
    if not content or len(content.split()) < 150:
        rendered_html = await asyncio.to_thread(_get_playwright_html, url)
        if rendered_html:
            try:
                _, title, text = await asyncio.to_thread(_run_newspaper, url, rendered_html)
                playwright_content = _normalize(f"{title}\n\n{text}" if title else text)
                if playwright_content and len(playwright_content.split()) > len((content or "").split()):
                    content = playwright_content
                    method = "playwright"
            except Exception:
                pass

    if not content or len(content.split()) < 50:
        return ExtractionResult(
            content="", source=url, input_type="url",
            word_count=0, extraction_method=method,
            error=(
                "Could not extract meaningful content from this page. "
                "It may be highly dynamic, require login, or contain no readable text. "
                "Please paste the text directly as input instead."
            ),
        )

    return ExtractionResult(
        content=content, source=url, input_type="url",
        word_count=len(content.split()),
        extraction_method=method, error=None,
    )


async def extract_from_url(url: str) -> ExtractionResult:
    url = clean_url(url)
    url_type = detect_url_type(url)

    extractors = {
        "reddit":  extract_reddit,
        "pdf_url": extract_pdf_url,
        "generic": extract_generic,
    }

    return await extractors[url_type](url)


# ---------------------------------------------------------------------------
# Raw text extractor
# ---------------------------------------------------------------------------

async def extract_from_text(text: str) -> ExtractionResult:
    text = text.strip()

    if not text:
        return ExtractionResult(
            content="", source="raw_text", input_type="text",
            word_count=0, extraction_method="raw_text",
            error="Input text is empty.",
        )

    return ExtractionResult(
        content=text, source="raw_text", input_type="text",
        word_count=len(text.split()),
        extraction_method="raw_text", error=None,
    )


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

MAX_TEXT_LENGTH = 50_000  # ~10,000 words


async def extract(request: ExtractRequest) -> ExtractionResult:
    inp = request.input.strip()

    if not inp:
        raise ValueError("Input cannot be empty.")

    if _is_url(inp):
        return await extract_from_url(inp)

    if len(inp) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters (~10,000 words). Please shorten the input."
        )

    return await extract_from_text(inp)


# ---------------------------------------------------------------------------
# Local testing
# ---------------------------------------------------------------------------

async def _main():
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python -m src.extractor <url or text>")
        return

    request = ExtractRequest(input=" ".join(sys.argv[1:]))
    result = await extract(request)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    print("\n--- content ---\n")
    print(result.content)


if __name__ == "__main__":
    asyncio.run(_main())
