# Clearview API

A document intelligence API that analyzes articles and web pages for bias, scam likelihood, and subjectivity — delivering results as a formatted PDF report or spoken audio.

**Docs:** [clearwayapi.tech/docs](https://clearwayapi.tech/docs)

---

## Quickstart

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows (bash)
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Copy `.env.example` to `.env` and fill in your `OPENAI_API_KEY` and `ELEVENLABS_API_KEY`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/clearview` | Analyze a document and receive a PDF report |
| `POST` | `/audio` | Convert a document to an MP3 audio file |

See the [full documentation](https://clearwayapi.tech/docs) for request/response schemas and code examples.
