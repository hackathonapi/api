# Clearview API

A document intelligence API that analyzes articles, web pages, and PDFs for bias, scam likelihood, and subjectivity — delivering results as a formatted PDF report or spoken audio.

**Docs:** [clearwayapi.tech/docs](https://clearwayapi.tech/docs)

---

## How it works

1. **Extract** — a URL or raw text is scraped and cleaned into plain content
2. **Analyze** — OpenAI GPT-4o-mini evaluates the content for scam signals, subjectivity, and bias, returning structured verdicts (`YES/NO`) alongside human-readable explanations
3. **Report** — results are compiled into a multi-page Clearview PDF (summary, analysis, source)
4. **Audio** — the extracted text is narrated via ElevenLabs TTS (with a gTTS fallback)

---

## Tech stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| AI analysis | OpenAI GPT-4o-mini |
| Text-to-speech | ElevenLabs (`eleven_turbo_v2_5`) / gTTS fallback |
| PDF generation | fpdf2 |
| Web scraping | newspaper4k, PyMuPDF |
| Storage | Firebase |

---

## Built with Claude

This project was developed with [Claude](https://claude.ai) (Anthropic) as an AI pair programmer throughout the hackathon. Claude was used to:

- Design and implement the unified analysis service (`analysis_service.py`), replacing three separate HuggingFace classifier pipelines with a single GPT-4o-mini call
- Architect the structured YES/NO verdict parsing system — prompting GPT to emit `SCAM: YES/NO`, `SUBJECTIVE: YES/NO`, and `BIASED: YES/NO` as machine-readable first lines, then using regex to extract verdicts and drive frontend color-coding
- Build the PDF generation pipeline with fpdf2
- Write and refactor the extraction, audio, and routing layers
- Debug merge conflicts and port features across architectural changes

---

## Quickstart

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows (bash)
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Create a `.env` file with the following keys:

```
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
```

ElevenLabs is optional — the API falls back to gTTS if the key is absent.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/clearview` | Analyze a document and receive a Clearview PDF report |
| `POST` | `/audio` | Convert a document to an MP3 audio file |

See the [full documentation](https://clearwayapi.tech/docs) for request/response schemas and code examples.
