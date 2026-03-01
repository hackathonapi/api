import logging

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# TEMPORARILY DISABLED

async def save_clearway(record_id: str, metadata: dict, pdf_bytes: bytes) -> None:
    logger.info("Firebase disabled — skipping save_clearway(%s).", record_id)


async def get_clearway(record_id: str) -> tuple[dict, bytes]:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Firebase storage is currently disabled.",
    )


async def save_audio(record_id: str, metadata: dict, mp3_bytes: bytes) -> None:
    logger.info("Firebase disabled — skipping save_audio(%s).", record_id)


async def get_audio(record_id: str) -> tuple[dict, bytes]:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Firebase storage is currently disabled.",
    )
