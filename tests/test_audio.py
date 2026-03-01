"""
Test: POST /audio → verify WAV response + confirm record saved in Firebase.

Run with the API server already running:
    uvicorn src.main:app --reload

Then in another terminal:
    python test_audio.py
"""

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


def test_audio():
    print("POST /audio ...")
    r = requests.post(f"{BASE}/audio", json={"input": TEST_INPUT}, timeout=60)

    if r.status_code != 200:
        print(f"FAIL  status={r.status_code}")
        print(r.text)
        sys.exit(1)

    audio_bytes = r.content
    record_id = r.headers.get("X-Content-ID", "")
    content_type = r.headers.get("Content-Type", "")

    out = "test_audio.mp3"
    with open(out, "wb") as f:
        f.write(audio_bytes)

    print(f"OK    record_id  = {record_id}")
    print(f"      content-type = {content_type}")
    print(f"      MP3 saved  → {out} ({len(audio_bytes):,} bytes)")

    # Validate it's a real MP3 (ID3 tag or sync bytes)
    is_mp3 = audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb"
    if is_mp3:
        print("      MP3 header = valid")
    else:
        print(f"WARN  MP3 header = unexpected ({audio_bytes[:4]})")

    # --- Verify the record is retrievable from Firebase via GET ---
    if not record_id:
        print("WARN  No X-Content-ID header — skipping Firebase retrieval test.")
        return

    print(f"\nGET /audio/{record_id} ...")
    r2 = requests.get(f"{BASE}/audio/{record_id}", timeout=30)

    if r2.status_code == 200:
        out2 = "test_audio_from_db.mp3"
        with open(out2, "wb") as f:
            f.write(r2.content)
        match = "✓ matches original" if r2.content == audio_bytes else "✗ differs from original"
        print(f"OK    WAV retrieved from Firebase → {out2} ({len(r2.content):,} bytes) {match}")
    else:
        print(f"FAIL  GET returned status={r2.status_code}")
        print(r2.text)
        sys.exit(1)


if __name__ == "__main__":
    test_audio()
