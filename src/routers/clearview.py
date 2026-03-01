import asyncio
import base64
import uuid

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from ..models.models import ClearviewResponse
from ..services.extractor_service import extract
from ..services.summarizer_service import summarize
from ..services.clearview_service import generate_clearview
from ..services.audio_service import generate_audio, DEFAULT_VOICE_ID
from ..services import firebase_service

router = APIRouter(tags=["Clearways"])


# ─────────────────────────────────────────────
# POST /clearview
# Extract → Summarize → Generate PDF → Save to Firebase
# ─────────────────────────────────────────────

@router.post("/clearview", response_model=ClearviewResponse)
async def clearview_route(input: str = Body(embed=True)) -> ClearviewResponse:
    # 1. Extract
    try:
        extraction = await extract(input)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if extraction.error or not extraction.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=extraction.error or "Could not extract content.",
        )

    # 2. Summarize
    summary_text, _ = await summarize(extraction.content, max(1, min(extraction.word_count / 100, 20)))

    # 3. Generate PDF
    try:
        pdf_bytes = await asyncio.to_thread(
            generate_clearview,
            extraction.title,
            extraction.content,
            extraction.source,
            extraction.word_count,
            summary_text,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clearview generation failed: {exc}",
        )

    # 4. Save to Firebase
    record_id = str(uuid.uuid4())
    await firebase_service.save_clearway(
        record_id,
        {
            "title": extraction.title or "Article Clearview",
            "content": extraction.content,
            "source": extraction.source,
            "word_count": extraction.word_count,
            "summary": summary_text,
        },
        pdf_bytes,
    )

    return ClearviewResponse(
        id=record_id,
        title=extraction.title or "Article Clearview",
        content=extraction.content,
        source=extraction.source,
        word_count=extraction.word_count,
        summary=summary_text,
        pdf=base64.b64encode(pdf_bytes).decode(),
    )


# ─────────────────────────────────────────────
# GET /clearview/{record_id}
# Download the PDF file for a previously generated Clearview
# ─────────────────────────────────────────────

@router.get("/clearview/{record_id}")
async def get_clearview_route(record_id: str) -> Response:
    meta, pdf_bytes = await firebase_service.get_clearway(record_id)
    filename = meta.get("title", record_id).replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


# ─────────────────────────────────────────────
# POST /audio
# Extract → Generate audio via ElevenLabs → Save to Firebase
# ─────────────────────────────────────────────

@router.post("/audio", response_class=StreamingResponse)
async def audio_route(
    input: str = Body(...),
    voice_id: str = Body(default=DEFAULT_VOICE_ID),
) -> StreamingResponse:
    try:
        audio_bytes, extraction = await generate_audio(input, voice_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    # Save to Firebase
    record_id = str(uuid.uuid4())
    await firebase_service.save_audio(
        record_id,
        {
            "title": extraction.title,
            "content": extraction.content,
            "source": extraction.source,
            "word_count": extraction.word_count,
        },
        audio_bytes,
    )

    return StreamingResponse(
        content=iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="audio.mp3"',
            "Content-Length": str(len(audio_bytes)),
            "X-Content-ID": record_id,
        },
    )


# ─────────────────────────────────────────────
# GET /audio/{record_id}
# Download the MP3 file for a previously generated audiobook
# ─────────────────────────────────────────────

@router.get("/audio/{record_id}")
async def get_audio_route(record_id: str) -> Response:
    meta, mp3_bytes = await firebase_service.get_audio(record_id)
    filename = meta.get("title", record_id).replace("/", "-")
    return Response(
        content=mp3_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{filename}.mp3"'},
    )
