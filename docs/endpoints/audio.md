# Audio — Text-to-Speech

## POST /audio

Accepts a URL, file path, or raw text and returns generated MP3 audio.

### Request

**Body** — `application/json`

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | `string` | Yes | URL, local file path, or raw text to convert |

```json
{
  "input": "https://example.com/article"
}
```

### Response

**200 OK** — `audio/mpeg`

Headers:

| Header | Value |
|---|---|
| `Content-Type` | `audio/mpeg` |
| `Content-Disposition` | `inline; filename="audio.mp3"` |
| `Content-Length` | Audio size in bytes |

**422 Unprocessable Entity** — content could not be extracted.

**503 Service Unavailable** — text-to-speech generation failed.
