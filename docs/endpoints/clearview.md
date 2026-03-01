# Clearview — Analysis & PDF

These endpoints analyze a document for bias, scam likelihood, and subjectivity, then produce a downloadable PDF report.

---

## POST /clearview

Accepts a URL, file path, or raw text. Runs four analyses in parallel (summarization, scam detection, objectivity, bias), generates a PDF report, and returns everything in a single response.

!!! note "Processing time"
    Several ML models run in parallel. Expect **10–30 seconds** depending on document length.

### Request

**Body** — `application/json`

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | `string` | Yes | A URL to an article, a local file path, or raw text to analyze |

```json
{
  "input": "https://example.com/article"
}
```

### Response

**200 OK** — `application/json`

| Field | Type | Description |
|---|---|---|
| `id` | `string` | UUID — use with `GET /clearview/{id}` to retrieve the PDF later |
| `title` | `string` | Extracted document title |
| `content` | `string` | Full extracted text |
| `source` | `string` | Source URL or path |
| `word_count` | `integer` | Total word count of the extracted content |
| `summary` | `string \| null` | Auto-generated summary |
| `is_scam` | `boolean` | Whether the content was flagged as potentially fraudulent |
| `scam_notes` | `string \| null` | Explanation of the scam classification |
| `is_subjective` | `boolean` | Whether the content is predominantly opinionated/editorial |
| `subjective_notes` | `string \| null` | Explanation of the objectivity classification |
| `biases` | `string[]` | List of bias labels detected above the confidence threshold |
| `bias_notes` | `string \| null` | Explanation of the bias classification |
| `pdf` | `string` | Base64-encoded PDF report |
| `error` | `string \| null` | Non-null if a non-fatal error occurred during processing |

**422 Unprocessable Entity** — content could not be extracted from the input.

**500 Internal Server Error** — PDF generation failed.

### Examples

=== "curl"

    ```bash
    curl -X POST https://clearwayapi.tech/clearview \
      -H "Content-Type: application/json" \
      -d '{"input": "https://www.bbc.com/news/articles/example"}'
    ```

=== "Python"

    ```python
    import httpx
    import base64

    r = httpx.post(
        "https://clearwayapi.tech/clearview",
        json={"input": "https://www.bbc.com/news/articles/example"},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()

    print("Record ID:", data["id"])
    print("Is scam:", data["is_scam"])
    print("Is subjective:", data["is_subjective"])
    print("Biases detected:", data["biases"])

    # Save the PDF report
    pdf_bytes = base64.b64decode(data["pdf"])
    with open("report.pdf", "wb") as f:
        f.write(pdf_bytes)
    ```

=== "JavaScript"

    ```js
    const res = await fetch("https://clearwayapi.tech/clearview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "https://www.bbc.com/news/articles/example" }),
    });

    if (!res.ok) throw new Error(`Error: ${res.status}`);
    const data = await res.json();

    console.log("Record ID:", data.id);
    console.log("Is scam:", data.is_scam);
    console.log("Biases:", data.biases);

    // Decode and download the PDF
    const bytes = atob(data.pdf);
    const arr = new Uint8Array(bytes.length).map((_, i) => bytes.charCodeAt(i));
    const blob = new Blob([arr], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.title}.pdf`;
    a.click();
    ```

### Example response

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Example News Article",
  "content": "Full extracted article text...",
  "source": "https://www.bbc.com/news/articles/example",
  "word_count": 842,
  "summary": "A brief summary of the article...",
  "is_scam": false,
  "scam_notes": null,
  "is_subjective": true,
  "subjective_notes": "The article uses strongly opinionated language in several sections.",
  "biases": ["political_left", "emotional_appeal"],
  "bias_notes": "Two bias types exceeded the confidence threshold.",
  "pdf": "<base64-encoded PDF>",
  "error": null
}
```

---

## GET /clearview/{record\_id}

Downloads the PDF report for a previously processed document. The `record_id` is the `id` field returned by `POST /clearview`.

### Request

**Path parameter**

| Parameter | Type | Description |
|---|---|---|
| `record_id` | `string` | UUID returned in the `id` field of a `POST /clearview` response |

### Response

**200 OK** — `application/pdf`

The PDF file is returned as a binary stream.

| Header | Value |
|---|---|
| `Content-Type` | `application/pdf` |
| `Content-Disposition` | `attachment; filename="<title>.pdf"` |

**404 Not Found** — no record exists for the given ID.

### Examples

=== "curl"

    ```bash
    curl -o report.pdf \
      "https://clearwayapi.tech/clearview/3fa85f64-5717-4562-b3fc-2c963f66afa6"
    ```

=== "Python"

    ```python
    import httpx

    record_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    r = httpx.get(f"https://clearwayapi.tech/clearview/{record_id}")
    r.raise_for_status()

    with open("report.pdf", "wb") as f:
        f.write(r.content)
    print("PDF saved.")
    ```

=== "JavaScript"

    ```js
    const recordId = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
    const res = await fetch(`https://clearwayapi.tech/clearview/${recordId}`);

    if (!res.ok) throw new Error(`Error: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "report.pdf";
    a.click();
    ```
