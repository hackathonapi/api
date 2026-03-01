import asyncio
import os
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore, storage
from fastapi import HTTPException, status


def _init_firebase() -> None:
    if firebase_admin._apps:
        return
    creds_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")
    if not creds_path or not bucket:
        raise RuntimeError(
            "Firebase not configured: set FIREBASE_CREDENTIALS_PATH and "
            "FIREBASE_STORAGE_BUCKET in .env"
        )
    cred = credentials.Certificate(creds_path)
    firebase_admin.initialize_app(cred, {"storageBucket": bucket})


# ─────────────────────────────────────────────
# Clearway
# ─────────────────────────────────────────────

async def save_clearway(record_id: str, metadata: dict, pdf_bytes: bytes) -> None:
    _init_firebase()
    storage_path = f"clearway/{record_id}.pdf"

    def _run() -> None:
        bucket = storage.bucket()
        bucket.blob(storage_path).upload_from_string(pdf_bytes, content_type="application/pdf")

        db = firestore.client()
        db.collection("clearway").document(record_id).set({
            **metadata,
            "storage_path": storage_path,
            "created_at": datetime.now(timezone.utc),
        })

    await asyncio.to_thread(_run)


async def get_clearway(record_id: str) -> tuple[dict, bytes]:
    _init_firebase()

    def _run() -> tuple[dict | None, bytes | None]:
        db = firestore.client()
        doc = db.collection("clearway").document(record_id).get()
        if not doc.exists:
            return None, None
        meta = doc.to_dict()
        pdf_bytes = storage.bucket().blob(meta["storage_path"]).download_as_bytes()
        return meta, pdf_bytes

    meta, pdf_bytes = await asyncio.to_thread(_run)
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clearway record '{record_id}' not found.",
        )
    return meta, pdf_bytes


# ─────────────────────────────────────────────
# Audio
# ─────────────────────────────────────────────

async def save_audio(record_id: str, metadata: dict, mp3_bytes: bytes) -> None:
    _init_firebase()
    storage_path = f"audio/{record_id}.mp3"

    def _run() -> None:
        bucket = storage.bucket()
        bucket.blob(storage_path).upload_from_string(mp3_bytes, content_type="audio/mpeg")

        db = firestore.client()
        db.collection("audio").document(record_id).set({
            **metadata,
            "storage_path": storage_path,
            "created_at": datetime.now(timezone.utc),
        })

    await asyncio.to_thread(_run)


async def get_audio(record_id: str) -> tuple[dict, bytes]:
    _init_firebase()

    def _run() -> tuple[dict | None, bytes | None]:
        db = firestore.client()
        doc = db.collection("audio").document(record_id).get()
        if not doc.exists:
            return None, None
        meta = doc.to_dict()
        mp3_bytes = storage.bucket().blob(meta["storage_path"]).download_as_bytes()
        return meta, mp3_bytes

    meta, mp3_bytes = await asyncio.to_thread(_run)
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio record '{record_id}' not found.",
        )
    return meta, mp3_bytes
