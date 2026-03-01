import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, firestore, storage
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# ── Initialise Firebase app once ─────────────────────────────────────────────

_bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")

if not firebase_admin._apps:
    _cred_value = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    try:
        cred = credentials.Certificate(json.loads(_cred_value))
    except (json.JSONDecodeError, ValueError):
        cred = credentials.Certificate(_cred_value)
    firebase_admin.initialize_app(cred, {"storageBucket": _bucket_name})

_db = firestore.client()
_bucket = storage.bucket()


# ── Clearview ─────────────────────────────────────────────────────────────────

async def save_clearway(record_id: str, metadata: dict, pdf_bytes: bytes) -> None:
    _db.collection("clearview").document(record_id).set(metadata)

    blob = _bucket.blob(f"clearview/{record_id}.pdf")
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")

    logger.info("Saved clearview record %s to Firebase.", record_id)


async def get_clearway(record_id: str) -> tuple[dict, bytes]:
    doc = _db.collection("clearview").document(record_id).get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clearview record '{record_id}' not found.",
        )

    blob = _bucket.blob(f"clearview/{record_id}.pdf")
    if not blob.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF for clearview record '{record_id}' not found in storage.",
        )

    pdf_bytes = blob.download_as_bytes()
    return doc.to_dict(), pdf_bytes


# ── Audio ─────────────────────────────────────────────────────────────────────

async def save_audio(record_id: str, metadata: dict, mp3_bytes: bytes) -> None:
    _db.collection("audio").document(record_id).set(metadata)

    blob = _bucket.blob(f"audio/{record_id}.mp3")
    blob.upload_from_string(mp3_bytes, content_type="audio/mpeg")

    logger.info("Saved audio record %s to Firebase.", record_id)


async def get_audio(record_id: str) -> tuple[dict, bytes]:
    doc = _db.collection("audio").document(record_id).get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio record '{record_id}' not found.",
        )

    blob = _bucket.blob(f"audio/{record_id}.mp3")
    if not blob.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MP3 for audio record '{record_id}' not found in storage.",
        )

    mp3_bytes = blob.download_as_bytes()
    return doc.to_dict(), mp3_bytes
