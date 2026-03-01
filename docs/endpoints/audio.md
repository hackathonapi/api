# Audio — Text-to-Speech

These endpoints convert a document (URL, file, or raw text) to an MP3 audio file using ElevenLabs.

---

## POST /audio

Extracts content from the input, generates speech via ElevenLabs, saves the result, and streams the MP3 back to the client. The record ID for later retrieval is returned in the `X-Content-ID` response header.

### Request

**Body** — `application/json`

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | `string` | Yes | A URL to an article, a local file path, or raw text to convert |
| `voice_id` | `string \| null` | No | ElevenLabs voice ID. Omit to use the default voice. |

```json
{
  "input": "https://example.com/article",
  "voice_id": null
}
```

### Response

**200 OK** — `audio/mpeg`

The MP3 is streamed directly. Key response headers:

| Header | Value |
|---|---|
| `Content-Type` | `audio/mpeg` |
| `Content-Disposition` | `inline; filename="audio.mp3"` |
| `Content-Length` | Size of the audio file in bytes |
| `X-Content-ID` | UUID — save this to retrieve the audio later via `GET /audio/{id}` |

!!! warning "Save the X-Content-ID header"
    The record ID is only returned in the `X-Content-ID` response header. There is no JSON body. Read this header if you need to retrieve the audio later.

**422 Unprocessable Entity** — content could not be extracted from the input.

**503 Service Unavailable** — ElevenLabs API error.

### Examples

=== "curl"

    ```bash
    # Save the audio file and print the record ID from the header
    curl -X POST https://clearwayapi.tech/audio \
      -H "Content-Type: application/json" \
      -d '{"input": "https://www.bbc.com/news/articles/example"}' \
      -o audio.mp3 \
      -D headers.txt

    # Extract the record ID
    grep -i "x-content-id" headers.txt
    ```

=== "Python"

    ```python
    import httpx

    r = httpx.post(
        "https://clearwayapi.tech/audio",
        json={"input": "https://www.bbc.com/news/articles/example"},
        timeout=120,
    )
    r.raise_for_status()

    record_id = r.headers["x-content-id"]
    print("Record ID:", record_id)

    with open("audio.mp3", "wb") as f:
        f.write(r.content)
    print("Saved audio.mp3")
    ```

=== "JavaScript"

    ```js
    const res = await fetch("https://clearwayapi.tech/audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "https://www.bbc.com/news/articles/example" }),
    });

    if (!res.ok) throw new Error(`Error: ${res.status}`);

    const recordId = res.headers.get("x-content-id");
    console.log("Record ID:", recordId);

    // Download the audio
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audio.mp3";
    a.click();
    ```

### Using a custom voice

Pass an ElevenLabs voice ID in the `voice_id` field. You can browse available voices in the [ElevenLabs Voice Library](https://elevenlabs.io/voice-library).

=== "curl"

    ```bash
    curl -X POST https://clearwayapi.tech/audio \
      -H "Content-Type: application/json" \
      -d '{"input": "https://example.com/article", "voice_id": "pNInz6obpgDQGcFmaJgB"}'
    ```

=== "Python"

    ```python
    r = httpx.post(
        "https://clearwayapi.tech/audio",
        json={
            "input": "https://example.com/article",
            "voice_id": "pNInz6obpgDQGcFmaJgB",
        },
        timeout=120,
    )
    ```

=== "JavaScript"

    ```js
    const res = await fetch("https://clearwayapi.tech/audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input: "https://example.com/article",
        voice_id: "pNInz6obpgDQGcFmaJgB",
      }),
    });
    ```

---

## GET /audio/{record\_id}

Downloads a previously generated MP3. The `record_id` is the value of the `X-Content-ID` header returned by `POST /audio`.

### Request

**Path parameter**

| Parameter | Type | Description |
|---|---|---|
| `record_id` | `string` | UUID from the `X-Content-ID` header of a `POST /audio` response |

### Response

**200 OK** — `audio/mpeg`

| Header | Value |
|---|---|
| `Content-Type` | `audio/mpeg` |
| `Content-Disposition` | `attachment; filename="<title>.mp3"` |

**404 Not Found** — no record exists for the given ID.

### Examples

=== "curl"

    ```bash
    curl -o audio.mp3 \
      "https://clearwayapi.tech/audio/3fa85f64-5717-4562-b3fc-2c963f66afa6"
    ```

=== "Python"

    ```python
    import httpx

    record_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    r = httpx.get(f"https://clearwayapi.tech/audio/{record_id}")
    r.raise_for_status()

    with open("audio.mp3", "wb") as f:
        f.write(r.content)
    print("Saved audio.mp3")
    ```

=== "JavaScript"

    ```js
    const recordId = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
    const res = await fetch(`https://clearwayapi.tech/audio/${recordId}`);

    if (!res.ok) throw new Error(`Error: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audio.mp3";
    a.click();
    ```
