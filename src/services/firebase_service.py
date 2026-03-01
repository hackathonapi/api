import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, storage
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def _init_firebase() -> None:
    if firebase_admin._apps:
        return
    creds_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")
    if not creds_path or not bucket_name:
        raise RuntimeError(
            "Firebase not configured: set FIREBASE_CREDENTIALS_PATH and "
            "FIREBASE_STORAGE_BUCKET in .env"
        )
    cred = credentials.Certificate(creds_path)
    firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})


# ─────────────────────────────────────────────
# Clearview  →  /clearview/{record_id}
# ─────────────────────────────────────────────

async def save_clearway(record_id: str, metadata: dict, pdf_bytes: bytes) -> None:
    try:
        _init_firebase()

        def _run() -> None:
            bucket = storage.bucket()
            meta_blob = bucket.blob(f"clearview/{record_id}/metadata.json")
            meta_blob.upload_from_string(
                json.dumps({**metadata, "created_at": datetime.now(timezone.utc).isoformat()}),
                content_type="application/json",
            )
            pdf_blob = bucket.blob(f"clearview/{record_id}/document.pdf")
            pdf_blob.upload_from_string(pdf_bytes, content_type="application/pdf")

        await asyncio.to_thread(_run)
    except Exception as exc:
        logger.warning("Firebase save_clearway failed (%s); continuing.", exc)


async def get_clearway(record_id: str) -> tuple[dict, bytes]:
    _init_firebase()

    def _run() -> tuple[dict, bytes] | None:
        bucket = storage.bucket()
        meta_blob = bucket.blob(f"clearview/{record_id}/metadata.json")
        if not meta_blob.exists():
            return None
        metadata = json.loads(meta_blob.download_as_text())
        pdf_bytes = bucket.blob(f"clearview/{record_id}/document.pdf").download_as_bytes()
        return metadata, pdf_bytes

    result = await asyncio.to_thread(_run)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clearview record '{record_id}' not found.",
        )
    return result


# ─────────────────────────────────────────────
# Audio  →  /audio/{record_id}
# ─────────────────────────────────────────────

async def save_audio(record_id: str, metadata: dict, mp3_bytes: bytes) -> None:
    try:
        _init_firebase()

        def _run() -> None:
            bucket = storage.bucket()
            meta_blob = bucket.blob(f"audio/{record_id}/metadata.json")
            meta_blob.upload_from_string(
                json.dumps({**metadata, "created_at": datetime.now(timezone.utc).isoformat()}),
                content_type="application/json",
            )
            audio_blob = bucket.blob(f"audio/{record_id}/audio.mp3")
            audio_blob.upload_from_string(mp3_bytes, content_type="audio/mpeg")

        await asyncio.to_thread(_run)
    except Exception as exc:
        logger.warning("Firebase save_audio failed (%s); continuing.", exc)


async def get_audio(record_id: str) -> tuple[dict, bytes]:
    _init_firebase()

    def _run() -> tuple[dict, bytes] | None:
        bucket = storage.bucket()
        meta_blob = bucket.blob(f"audio/{record_id}/metadata.json")
        if not meta_blob.exists():
            return None
        metadata = json.loads(meta_blob.download_as_text())
        mp3_bytes = bucket.blob(f"audio/{record_id}/audio.mp3").download_as_bytes()
        return metadata, mp3_bytes

    result = await asyncio.to_thread(_run)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio record '{record_id}' not found.",
        )
    return result
