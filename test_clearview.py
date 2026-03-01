"""
Test: POST /clearview with a NOAA climate article URL.

Run with the API server already running:
    uvicorn src.main:app --reload

Then in another terminal:
    python test_clearview.py
"""

import sys
import json
import requests

BASE = "http://127.0.0.1:8000"
TEST_URL = "https://www.noaa.gov/education/resource-collections/climate/climate-change-impacts"


def test_clearview():
    print(f"POST /clearview — {TEST_URL}")
    r = requests.post(
        f"{BASE}/clearview",
        json={"input": TEST_URL},
        timeout=120,
    )

    if r.status_code != 200:
        print(f"FAIL  status={r.status_code}")
        print(r.text)
        sys.exit(1)

    data = r.json()

    print(f"OK    title        = {data.get('title', '—')}")
    print(f"      word_count   = {data.get('word_count', '—')}")
    print(f"      source       = {data.get('source', '—')}")
    print(f"      is_scam      = {data.get('is_scam')}")
    print(f"      is_subjective= {data.get('is_subjective')}")
    print(f"      biases       = {data.get('biases')}")
    print(f"      summary      = {str(data.get('summary', ''))[:120]}...")

    # Save PDF locally
    pdf_b64 = data.get("pdf")
    if pdf_b64:
        import base64
        pdf_bytes = base64.b64decode(pdf_b64)
        out = "test_clearview.pdf"
        with open(out, "wb") as f:
            f.write(pdf_bytes)
        print(f"      PDF saved    → {out} ({len(pdf_bytes):,} bytes)")
    else:
        print("WARN  No PDF in response.")

    print("\nFull response (minus pdf field):")
    display = {k: v for k, v in data.items() if k != "pdf"}
    print(json.dumps(display, indent=2))


if __name__ == "__main__":
    test_clearview()
