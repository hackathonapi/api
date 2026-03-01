import asyncio
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

def _do_save_clearway(record_id: str, metadata: dict, pdf_bytes: bytes) -> None:
    _db.collection("clearview").document(record_id).set(metadata)
    blob = _bucket.blob(f"clearview/{record_id}.pdf")
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")


async def save_clearway(record_id: str, metadata: dict, pdf_bytes: bytes) -> None:
    try:
        await asyncio.to_thread(_do_save_clearway, record_id, metadata, pdf_bytes)
        logger.info("Saved clearview record %s to Firebase.", record_id)
    except Exception as exc:
        logger.error("Firebase save_clearway failed for %s: %s", record_id, exc, exc_info=True)
        raise


async def get_clearway(record_id: str) -> tuple[dict, bytes]:
    doc = await asyncio.to_thread(_db.collection("clearview").document(record_id).get)
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clearview record '{record_id}' not found.",
        )

    blob = _bucket.blob(f"clearview/{record_id}.pdf")
    if not await asyncio.to_thread(blob.exists):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF for clearview record '{record_id}' not found in storage.",
        )

    pdf_bytes = await asyncio.to_thread(blob.download_as_bytes)
    return doc.to_dict(), pdf_bytes


# ── Audio ─────────────────────────────────────────────────────────────────────

def _do_save_audio(record_id: str, metadata: dict, mp3_bytes: bytes) -> None:
    _db.collection("audio").document(record_id).set(metadata)
    blob = _bucket.blob(f"audio/{record_id}.mp3")
    blob.upload_from_string(mp3_bytes, content_type="audio/mpeg")


async def save_audio(record_id: str, metadata: dict, mp3_bytes: bytes) -> None:
    try:
        await asyncio.to_thread(_do_save_audio, record_id, metadata, mp3_bytes)
        logger.info("Saved audio record %s to Firebase.", record_id)
    except Exception as exc:
        logger.error("Firebase save_audio failed for %s: %s", record_id, exc, exc_info=True)
        raise


async def get_audio(record_id: str) -> tuple[dict, bytes]:
    doc = await asyncio.to_thread(_db.collection("audio").document(record_id).get)
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio record '{record_id}' not found.",
        )

    blob = _bucket.blob(f"audio/{record_id}.mp3")
    if not await asyncio.to_thread(blob.exists):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MP3 for audio record '{record_id}' not found in storage.",
        )

    mp3_bytes = await asyncio.to_thread(blob.download_as_bytes)
    return doc.to_dict(), mp3_bytes
