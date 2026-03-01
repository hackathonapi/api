import asyncio
import base64
import logging
import os
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, db
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

def _init_firebase() -> None:
    if firebase_admin._apps:
        return
    import json
    database_url = os.environ.get("FIREBASE_DATABASE_URL")
    creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if not database_url or not creds_json:
        raise RuntimeError(
            "Firebase not configured: set FIREBASE_CREDENTIALS_JSON and "
            "FIREBASE_DATABASE_URL in .env"
        )
    cred = credentials.Certificate(json.loads(creds_json))
    firebase_admin.initialize_app(cred, {"databaseURL": database_url})


# ─────────────────────────────────────────────
# Clearview  →  /clearview/{record_id}
# ─────────────────────────────────────────────

async def save_clearway(record_id: str, metadata: dict, pdf_bytes: bytes) -> None:
    try:
        _init_firebase()

        def _run() -> None:
            db.reference(f"/clearview/{record_id}").set({
                **metadata,
                "pdf": base64.b64encode(pdf_bytes).decode("ascii"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        await asyncio.to_thread(_run)
    except Exception as exc:
        logger.warning("Firebase save_clearway failed (%s); continuing.", exc)


async def get_clearway(record_id: str) -> tuple[dict, bytes]:
    _init_firebase()

    def _run() -> dict | None:
        return db.reference(f"/clearview/{record_id}").get()

    data = await asyncio.to_thread(_run)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clearview record '{record_id}' not found.",
        )
    pdf_bytes = base64.b64decode(data.pop("pdf", ""))
    return data, pdf_bytes


# ─────────────────────────────────────────────
# Audio  →  /audio/{record_id}
# ─────────────────────────────────────────────

async def save_audio(record_id: str, metadata: dict, mp3_bytes: bytes) -> None:
    try:
        _init_firebase()

        def _run() -> None:
            db.reference(f"/audio/{record_id}").set({
                **metadata,
                "audio": base64.b64encode(mp3_bytes).decode("ascii"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        await asyncio.to_thread(_run)
    except Exception as exc:
        logger.warning("Firebase save_audio failed (%s); continuing.", exc)


async def get_audio(record_id: str) -> tuple[dict, bytes]:
    _init_firebase()

    def _run() -> dict | None:
        return db.reference(f"/audio/{record_id}").get()

    data = await asyncio.to_thread(_run)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio record '{record_id}' not found.",
        )
    mp3_bytes = base64.b64decode(data.pop("audio", ""))
    return data, mp3_bytes
