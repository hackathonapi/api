import os
import re
from enum import Enum
from typing import Optional
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs

import httpx
from bs4 import BeautifulSoup
from fastapi import UploadFile
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class InputType(str, Enum):
    URL = "url"
    FILE = "file"
    TEXT = "text"


class ExtractionResult(BaseModel):
    content: str
    input_type: InputType
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

class PaywallError(Exception):
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


def detect_paywall(url: str, soup: BeautifulSoup, raw_html: str) -> Optional[str]:
    domain = urlparse(url).netloc.lower().replace("www.", "")

    if any(domain.endswith(d) for d in KNOWN_PAYWALL_DOMAINS):
        return (
            f"'{domain}' is a known paywalled publication. "
            "Please access the content directly and paste the text."
        )

    html_lower = raw_html.lower()
    for signal in PAYWALL_SIGNALS:
        if signal in html_lower:
            return (
                f"This content appears to be behind a paywall (detected: '{signal}'). "
                "Please paste the text directly."
            )

    word_count = len(soup.get_text().split())
    if word_count < 120:
        return (
            "This page returned very little text and may be paywalled or require login. "
            "Please paste the text directly."
        )

    return None


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

    if domain in ("youtube.com", "youtu.be"):
        if "watch" in path or "youtu.be" in url or "/shorts/" in path:
            return "youtube"

    if domain in ("reddit.com", "old.reddit.com", "new.reddit.com"):
        return "reddit"

    if domain in ("twitter.com", "x.com"):
        return "twitter"

    if path.endswith(".pdf"):
        return "pdf_url"

    return "generic"


# ---------------------------------------------------------------------------
# Generic scraping helpers
# ---------------------------------------------------------------------------

NOISE_TAGS = [
    "script", "style", "nav", "footer", "header", "aside",
    "form", "button", "input", "select", "textarea", "iframe",
    "noscript", "svg", "figure", "figcaption", "advertisement",
]

NOISE_PATTERNS = [
    "cookie", "banner", "popup", "modal", "sidebar", "advertisement",
    "ad-", "ads-", "social", "share", "related", "recommended",
    "newsletter", "subscribe", "comment", "footer", "header", "nav",
]


def is_noise_element(tag) -> bool:
    classes = " ".join(tag.get("class", [])).lower()
    tag_id = tag.get("id", "").lower()
    combined = f"{classes} {tag_id}"
    return any(pattern in combined for pattern in NOISE_PATTERNS)


def extract_core_content(soup: BeautifulSoup) -> str:
    for tag in soup(NOISE_TAGS):
        tag.decompose()

    for tag in soup.find_all(True):
        if is_noise_element(tag):
            tag.decompose()

    content_candidates = [
        soup.find("article"),
        soup.find("main"),
        soup.find(attrs={"role": "main"}),
        soup.find(class_=re.compile(r"article|post|content|story|body", re.I)),
        soup.find(id=re.compile(r"article|post|content|story|body", re.I)),
        soup.find("body"),
    ]

    content_tag = next((c for c in content_candidates if c), None)
    if not content_tag:
        return ""

    text = content_tag.get_text(separator="\n", strip=True)
    return _normalize(text)


async def extract_with_beautifulsoup(url: str) -> Optional[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            paywall_result = detect_paywall(url, soup, response.text)
            if paywall_result:
                raise PaywallError(paywall_result)

            return extract_core_content(soup)

    except PaywallError:
        raise
    except Exception:
        return None


def extract_with_playwright(url: str) -> Optional[str]:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.route(
                "**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}",
                lambda route: route.abort(),
            )

            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)

            html = page.content()
            browser.close()

            soup = BeautifulSoup(html, "html.parser")
            return extract_core_content(soup)

    except Exception:
        return None


# ---------------------------------------------------------------------------
# URL extractors
# ---------------------------------------------------------------------------

def get_youtube_video_id(url: str) -> Optional[str]:
    pattern = r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


async def extract_youtube(url: str) -> ExtractionResult:
    video_id = get_youtube_video_id(url)

    if not video_id:
        return ExtractionResult(
            content="", source=url, input_type=InputType.URL,
            word_count=0, extraction_method="youtube_transcript",
            error="Could not extract video ID from URL",
        )

    try:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        except NoTranscriptFound:
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcripts.find_generated_transcript(["en"])
            transcript_list = transcript.fetch()

        text = " ".join(
            segment["text"].strip()
            for segment in transcript_list
            if segment["text"].strip()
        )

        text = re.sub(r'\[.*?\]', '', text)
        text = _normalize(text)

        if not text:
            return ExtractionResult(
                content="", source=url, input_type=InputType.URL,
                word_count=0, extraction_method="youtube_transcript",
                error="Transcript was empty after cleaning",
            )

        return ExtractionResult(
            content=text, source=url, input_type=InputType.URL,
            word_count=len(text.split()),
            extraction_method="youtube_transcript", error=None,
        )

    except TranscriptsDisabled:
        return ExtractionResult(
            content="", source=url, input_type=InputType.URL,
            word_count=0, extraction_method="youtube_transcript",
            error="This video has transcripts disabled by the creator",
        )
    except Exception as e:
        return ExtractionResult(
            content="", source=url, input_type=InputType.URL,
            word_count=0, extraction_method="youtube_transcript",
            error=f"No transcript available for this video: {str(e)}",
        )


async def extract_reddit(url: str) -> ExtractionResult:
    url = url.replace("www.reddit.com", "old.reddit.com")
    url = url.replace("new.reddit.com", "old.reddit.com")

    headers = {"User-Agent": "Mozilla/5.0 (compatible; accessibility-api/1.0)"}

    try:
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
                content="", source=url, input_type=InputType.URL,
                word_count=0, extraction_method="reddit_json",
                error="Post appears to be empty, deleted, or a link post with no body",
            )

        return ExtractionResult(
            content=content, source=url, input_type=InputType.URL,
            word_count=len(content.split()),
            extraction_method="reddit_json", error=None,
        )

    except Exception as e:
        return ExtractionResult(
            content="", source=url, input_type=InputType.URL,
            word_count=0, extraction_method="reddit_json",
            error=f"Could not extract Reddit post: {str(e)}",
        )


async def extract_twitter(url: str) -> ExtractionResult:
    return ExtractionResult(
        content="", source=url, input_type=InputType.URL,
        word_count=0, extraction_method="twitter",
        error=(
            "Twitter/X content cannot be extracted due to platform restrictions. "
            "Please paste the tweet text directly."
        ),
    )


async def extract_pdf_url(url: str) -> ExtractionResult:
    return ExtractionResult(
        content="", source=url, input_type=InputType.URL,
        word_count=0, extraction_method="pdf_url",
        error=(
            "PDF extraction from URLs is not supported. "
            "Please download the PDF and paste its text directly."
        ),
    )


async def extract_generic(url: str) -> ExtractionResult:
    try:
        content = await extract_with_beautifulsoup(url)
    except PaywallError as e:
        return ExtractionResult(
            content="", source=url, input_type=InputType.URL,
            word_count=0, extraction_method="beautifulsoup",
            error=str(e),
        )

    if not content or len(content.split()) < 150:
        playwright_content = extract_with_playwright(url)
        if playwright_content and len(playwright_content.split()) > len((content or "").split()):
            content = playwright_content
            method = "playwright"
        else:
            method = "beautifulsoup"
    else:
        method = "beautifulsoup"

    if not content or len(content.split()) < 50:
        return ExtractionResult(
            content="", source=url, input_type=InputType.URL,
            word_count=0, extraction_method=method,
            error=(
                "Could not extract meaningful content from this page. "
                "It may be dynamic, require login, or contain no readable text."
            ),
        )

    return ExtractionResult(
        content=content, source=url, input_type=InputType.URL,
        word_count=len(content.split()),
        extraction_method=method, error=None,
    )


async def extract_from_url(url: str) -> ExtractionResult:
    url = clean_url(url)
    url_type = detect_url_type(url)

    extractors = {
        "youtube": extract_youtube,
        "reddit": extract_reddit,
        "twitter": extract_twitter,
        "pdf_url": extract_pdf_url,
        "generic": extract_generic,
    }

    return await extractors[url_type](url)


# ---------------------------------------------------------------------------
# File extractor
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst", ".csv",
    ".json", ".xml", ".html", ".htm", ".log",
}

ALLOWED_MIME_TYPES = {
    "text/plain", "text/markdown", "text/csv", "text/html",
    "text/xml", "application/json", "application/xml",
    "text/x-rst", "text/x-log",
}

MAX_SIZE_BYTES = 5 * 1024 * 1024


async def extract_from_file(file: UploadFile) -> ExtractionResult:
    filename = file.filename or "uploaded_file"
    extension = os.path.splitext(filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return ExtractionResult(
            content="", source=filename, input_type=InputType.FILE,
            word_count=0, extraction_method="file_read",
            error=(
                f"File type '{extension}' is not supported. "
                f"Only plain text files are accepted: "
                f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    raw_bytes = await file.read()

    if not raw_bytes:
        return ExtractionResult(
            content="", source=filename, input_type=InputType.FILE,
            word_count=0, extraction_method="file_read",
            error="The uploaded file is empty.",
        )

    if len(raw_bytes) > MAX_SIZE_BYTES:
        return ExtractionResult(
            content="", source=filename, input_type=InputType.FILE,
            word_count=0, extraction_method="file_read",
            error="File is too large. Maximum size is 5MB.",
        )

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw_bytes.decode("latin-1")
        except UnicodeDecodeError:
            return ExtractionResult(
                content="", source=filename, input_type=InputType.FILE,
                word_count=0, extraction_method="file_read",
                error="Could not decode file. Please ensure it is a valid text file saved as UTF-8.",
            )

    content = _normalize(content)

    if not content:
        return ExtractionResult(
            content="", source=filename, input_type=InputType.FILE,
            word_count=0, extraction_method="file_read",
            error="File contains no readable text after decoding.",
        )

    return ExtractionResult(
        content=content, source=filename, input_type=InputType.FILE,
        word_count=len(content.split()),
        extraction_method="file_read", error=None,
    )


# ---------------------------------------------------------------------------
# Raw text extractor
# ---------------------------------------------------------------------------

MAX_RAW_TEXT_LENGTH = 50_000


async def extract_from_text(text: str) -> ExtractionResult:
    text = _normalize(text)

    if not text:
        return ExtractionResult(
            content="", source="raw_text", input_type=InputType.TEXT,
            word_count=0, extraction_method="raw_text",
            error="Input text is empty.",
        )

    if len(text) > MAX_RAW_TEXT_LENGTH:
        return ExtractionResult(
            content="", source="raw_text", input_type=InputType.TEXT,
            word_count=0, extraction_method="raw_text",
            error=f"Text is too long. Maximum is {MAX_RAW_TEXT_LENGTH} characters (~10,000 words).",
        )

    return ExtractionResult(
        content=text, source="raw_text", input_type=InputType.TEXT,
        word_count=len(text.split()),
        extraction_method="raw_text", error=None,
    )


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

async def extract(
    text: Optional[str] = None,
    url: Optional[str] = None,
    file: Optional[UploadFile] = None,
) -> ExtractionResult:
    provided = sum([text is not None, url is not None, file is not None])

    if provided == 0:
        return ExtractionResult(
            content="", source="", input_type=InputType.TEXT,
            word_count=0, extraction_method="none",
            error="No input provided. Please provide one of: text, url, or file.",
        )

    if provided > 1:
        return ExtractionResult(
            content="", source="", input_type=InputType.TEXT,
            word_count=0, extraction_method="none",
            error="Only one input type can be provided at a time: text, url, or file.",
        )

    if url is not None:
        return await extract_from_url(url)

    if file is not None:
        return await extract_from_file(file)

    return await extract_from_text(text)


# ---------------------------------------------------------------------------
# Local testing
# ---------------------------------------------------------------------------

async def _main():
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extractor.py <url>")
        print("  python extractor.py --text 'your raw text here'")
        print("  python extractor.py --file path/to/file.txt")
        return

    flag = sys.argv[1]

    if flag == "--text":
        raw = " ".join(sys.argv[2:])
        result = await extract(text=raw)
    elif flag == "--file":
        path = sys.argv[2]

        class _FakeUploadFile:
            def __init__(self, path: str):
                self.filename = os.path.basename(path)
                self._path = path

            async def read(self) -> bytes:
                with open(self._path, "rb") as f:
                    return f.read()

        result = await extract(file=_FakeUploadFile(path))
    else:
        result = await extract(url=flag)

    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    print("\n--- content ---\n")
    print(result.content)


if __name__ == "__main__":
    import asyncio
    asyncio.run(_main())
