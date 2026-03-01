"""
Test: POST /clearview → verify response + confirm record saved in Firebase.

Run with the API server already running:
    uvicorn src.main:app --reload

Then in another terminal:
    python test_clearview.py
"""

import base64
import json
import sys
import requests

BASE = "http://127.0.0.1:8000"

TEST_INPUT = (
    "Scientists at MIT have developed a new type of solar panel that can generate "
    "electricity even at night by harvesting heat radiated from the Earth's surface. "
    "The thermoradiative cells work in reverse compared to standard photovoltaic panels, "
    "emitting infrared light into the cold night sky and producing a small but measurable "
    "current. Researchers say the technology could eventually supplement daytime solar "
    "generation and provide continuous renewable energy without battery storage."
)


def test_clearview():
    print("POST /clearview ...")
    r = requests.post(f"{BASE}/clearview", json={"input": TEST_INPUT}, timeout=120)

    if r.status_code != 200:
        print(f"FAIL  status={r.status_code}")
        print(r.text)
        sys.exit(1)

    data = r.json()

    record_id = data.get("id")
    print(f"OK    record_id={record_id}")
    print(f"      title      = {data.get('title')!r}")
    print(f"      word_count = {data.get('word_count')}")
    print(f"      is_scam    = {data.get('is_scam')}")
    print(f"      is_subj    = {data.get('is_subjective')}")
    print(f"      biases     = {data.get('biases')}")
    print(f"      summary    = {str(data.get('summary', ''))[:120]!r} ...")

    pdf_b64 = data.get("pdf", "")
    if pdf_b64:
        pdf_bytes = base64.b64decode(pdf_b64)
        out = "test_clearview.pdf"
        with open(out, "wb") as f:
            f.write(pdf_bytes)
        print(f"      PDF saved  → {out} ({len(pdf_bytes):,} bytes)")
    else:
        print("      PDF        = (none)")

    # --- Verify the record is retrievable from Firebase via GET ---
    if record_id:
        print(f"\nGET /clearview/{record_id} ...")
        r2 = requests.get(f"{BASE}/clearview/{record_id}", timeout=30)
        if r2.status_code == 200:
            out2 = "test_clearview_from_db.pdf"
            with open(out2, "wb") as f:
                f.write(r2.content)
            print(f"OK    PDF retrieved from Firebase → {out2} ({len(r2.content):,} bytes)")
        else:
            print(f"FAIL  GET returned status={r2.status_code}")
            print(r2.text)


if __name__ == "__main__":
    test_clearview()
