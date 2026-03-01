# Getting Started

This guide walks you through setting up and running the Clearview API locally, then making your first request.

---

## Prerequisites

- Python 3.9+
- `pip`
- API keys for the following services:

| Service | Used for |
|---|---|
| **OpenAI** | Summarization (`OPENAI_API_KEY`) |
| **ElevenLabs** | Text-to-speech (`ELEVENLABS_API_KEY`) |
| **Firebase** | Persistence — Firestore + Cloud Storage |

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/hackathonapi/api.git
cd api
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (bash)
# source .venv/bin/activate     # macOS / Linux
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
```

Place your Firebase service account file at `firebase-credentials.json` in the project root (download from the Firebase Console under Project Settings → Service Accounts).

---

## Running the API

```bash
uvicorn src.main:app --reload
```

The API starts at `http://127.0.0.1:8000`.

**Verify it's running:**

=== "curl"

    ```bash
    curl http://127.0.0.1:8000/
    ```

=== "Python"

    ```python
    import httpx

    r = httpx.get("http://127.0.0.1:8000/")
    print(r.json())
    ```

=== "JavaScript"

    ```js
    const res = await fetch("http://127.0.0.1:8000/");
    console.log(await res.json());
    ```

Expected response:

```json
{"message": "API is running!"}
```

---

## Interactive docs

FastAPI exposes auto-generated interactive docs while the server is running:

- **Swagger UI** — `http://127.0.0.1:8000/docs`
- **ReDoc** — `http://127.0.0.1:8000/redoc`

---

## Your first request

The following example analyzes a news article URL and retrieves the PDF report.

### Step 1 — Analyze a document

=== "curl"

    ```bash
    curl -X POST http://127.0.0.1:8000/clearview \
      -H "Content-Type: application/json" \
      -d '{"input": "https://www.bbc.com/news/articles/example"}'
    ```

=== "Python"

    ```python
    import httpx

    r = httpx.post(
        "http://127.0.0.1:8000/clearview",
        json={"input": "https://www.bbc.com/news/articles/example"},
        timeout=120,  # analysis takes time — several ML models run in parallel
    )
    data = r.json()
    print("Record ID:", data["id"])
    print("Is scam:", data["is_scam"])
    print("Biases detected:", data["biases"])
    ```

=== "JavaScript"

    ```js
    const res = await fetch("http://127.0.0.1:8000/clearview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "https://www.bbc.com/news/articles/example" }),
    });
    const data = await res.json();
    console.log("Record ID:", data.id);
    console.log("Is scam:", data.is_scam);
    console.log("Biases:", data.biases);
    ```

The response includes a `pdf` field containing the full report as a **base64-encoded string**, and an `id` you can use to retrieve the PDF later.

### Step 2 — Save the PDF

=== "Python"

    ```python
    import base64

    pdf_bytes = base64.b64decode(data["pdf"])
    with open("report.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("Saved report.pdf")
    ```

=== "JavaScript"

    ```js
    // In a browser
    const bytes = atob(data.pdf);
    const arr = new Uint8Array(bytes.length).map((_, i) => bytes.charCodeAt(i));
    const blob = new Blob([arr], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "report.pdf";
    a.click();
    ```

### Step 3 — Retrieve the PDF later by ID

=== "curl"

    ```bash
    curl -o report.pdf \
      "http://127.0.0.1:8000/clearview/<record_id>"
    ```

=== "Python"

    ```python
    r = httpx.get(f"http://127.0.0.1:8000/clearview/{data['id']}")
    with open("report.pdf", "wb") as f:
        f.write(r.content)
    ```

=== "JavaScript"

    ```js
    const pdfRes = await fetch(`http://127.0.0.1:8000/clearview/${data.id}`);
    const blob = await pdfRes.blob();
    const url = URL.createObjectURL(blob);
    // open or download the blob as needed
    ```

---

## Next steps

- [Clearview endpoint reference](endpoints/clearview.md) — full request/response details
- [Audio endpoint reference](endpoints/audio.md) — convert documents to speech
- [Models reference](reference/models.md) — complete schema definitions
