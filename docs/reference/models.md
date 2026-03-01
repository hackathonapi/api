# Models Reference

Complete schema definitions for all request and response models.

---

## Request models

### InputRequest

Used by `POST /clearview`.

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | `string` | Yes | A URL, file path, or raw text string to analyze |

```json
{
  "input": "https://example.com/article"
}
```

---

### AudioRequest

Used by `POST /audio`.

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | `string` | Yes | A URL, file path, or raw text string to convert |
| `voice_id` | `string \| null` | No | ElevenLabs voice ID. Defaults to the server's configured voice if omitted. |

```json
{
  "input": "https://example.com/article",
  "voice_id": null
}
```

---

## Response models

### ClearviewResponse

Returned by `POST /clearview`.

| Field | Type | Description |
|---|---|---|
| `title` | `string` | Extracted document title |
| `content` | `string` | Full extracted text content |
| `source` | `string` | Original source URL or input path |
| `word_count` | `integer` | Number of words in the extracted content |
| `summary` | `string \| null` | Auto-generated summary. `null` if summarization failed. |
| `scam_notes` | `string \| null` | Human-readable explanation of the scam classification |
| `subjective_notes` | `string \| null` | Human-readable explanation of the objectivity classification |
| `bias_notes` | `string \| null` | Human-readable explanation of detected biases |
| `ai_section` | `string \| null` | Combined analysis section text used in output |
| `pdf` | `string` | Base64-encoded PDF report. Decode with `base64.b64decode()` (Python) or `atob()` (JS). |
| `error` | `string \| null` | Non-null if a non-fatal error occurred during processing |

```json
{
  "title": "Example Article",
  "content": "Full article text...",
  "source": "https://example.com/article",
  "word_count": 842,
  "summary": "A brief summary.",
  "scam_notes": null,
  "subjective_notes": "The article contains editorial language.",
  "bias_notes": "One bias type exceeded the confidence threshold.",
  "ai_section": "Combined AI analysis content.",
  "pdf": "<base64 string>",
  "error": null
}
```

---

## Internal models

These models are used internally by the API and are not returned directly to clients, but are documented here for reference.

### ExtractionResult

Produced by the extractor service before analysis begins.

| Field | Type | Description |
|---|---|---|
| `title` | `string` | Extracted document title |
| `content` | `string` | Extracted text body |
| `input_type` | `string` | Classification of the input (`url`, `file`, or `text`) |
| `source` | `string` | Source identifier |
| `word_count` | `integer` | Word count of the extracted content |
| `extraction_method` | `string` | Method used to extract content (e.g. `newspaper4k`) |
| `error` | `string \| null` | Set if extraction partially failed |

---

### ScamAnalysisResult

| Field | Type | Description |
|---|---|---|
| `scam_probability` | `float` (0–1) | Confidence score that the content is a scam |
| `non_scam_probability` | `float` (0–1) | Confidence score that the content is legitimate |
| `is_scam` | `boolean` | Final classification |
| `notes` | `string \| null` | Explanation |
| `error` | `string \| null` | Set if analysis failed |

---

### ObjectivityAnalysisResult

| Field | Type | Description |
|---|---|---|
| `subjective_probability` | `float` (0–1) | Confidence the content is subjective/opinionated |
| `objective_probability` | `float` (0–1) | Confidence the content is objective/factual |
| `is_subjective` | `boolean` | Final classification |
| `notes` | `string \| null` | Explanation |
| `error` | `string \| null` | Set if analysis failed |

---

### SentimentAnalysisResult

| Field | Type | Description |
|---|---|---|
| `bias_cutoff` | `float` (0–1) | Minimum confidence score required for a bias label to be reported |
| `bias_scores` | `object` | Map of all bias category labels to their confidence scores |
| `biases_above_cutoff` | `string[]` | Labels whose scores met or exceeded `bias_cutoff` — surfaced as `biases` in `ClearviewResponse` |
| `notes` | `string \| null` | Explanation |
| `error` | `string \| null` | Set if analysis failed |
