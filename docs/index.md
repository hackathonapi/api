# Clearview API

Clearview is a document intelligence API that analyzes articles, web pages, and raw text for bias, scam likelihood, and subjectivity — then delivers results as a formatted PDF or spoken audio.

---

## What it does

| Feature | Description |
|---|---|
| **Bias detection** | Identifies political, ideological, and cultural biases in content |
| **Scam detection** | Flags misleading or fraudulent content |
| **Objectivity analysis** | Measures how subjective or editorial the writing is |
| **Summarization** | Generates a concise summary of the full text |
| **PDF report** | Bundles all findings into a downloadable report |
| **Text-to-speech** | Converts any document to an MP3 via ElevenLabs |

---

## Base URL

```
https://clearwayapi.tech
```

---

## Endpoints at a glance

| Method | Path | Description |
|---|---|---|
| `POST` | `/clearview` | Analyze a document and receive a PDF report |
| `GET` | `/clearview/{id}` | Download a previously generated PDF |
| `POST` | `/audio` | Convert a document to an MP3 audio file |
| `GET` | `/audio/{id}` | Download a previously generated MP3 |

---

## Quick links

- [Getting Started](getting-started.md) — set up and run your first request
- [Clearview endpoints](endpoints/clearview.md) — analysis + PDF
- [Audio endpoints](endpoints/audio.md) — text-to-speech
- [Models reference](reference/models.md) — full schema details
