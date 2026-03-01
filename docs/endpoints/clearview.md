# Clearview — Analysis & PDF

## POST /clearview

Accepts a URL, file path, or raw text. The API extracts content, runs analysis, and returns a base64-encoded PDF report in the JSON response.

### Request

**Body** — `application/json`

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | `string` | Yes | URL, local file path, or raw text to analyze |

```json
{
  "input": "https://example.com/article"
}
```

### Response

**200 OK** — `application/json`

| Field | Type | Description |
|---|---|---|
| `title` | `string` | Extracted document title |
| `content` | `string` | Full extracted text |
| `source` | `string` | Source URL or input path |
| `word_count` | `integer` | Word count of extracted content |
| `summary` | `string \| null` | Generated summary |
| `scam_notes` | `string \| null` | Scam analysis notes |
| `subjective_notes` | `string \| null` | Objectivity analysis notes |
| `bias_notes` | `string \| null` | Bias analysis notes |
| `ai_section` | `string \| null` | Combined AI analysis text |
| `pdf` | `string` | Base64-encoded PDF report |
| `error` | `string \| null` | Non-fatal error detail if present |

**422 Unprocessable Entity** — content could not be extracted.

**500 Internal Server Error** — PDF generation failed.
