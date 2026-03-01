import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from ..models.models import AudioRequest
from ..services.audio_service import generate_audio, DEFAULT_VOICE_ID
from ..services import firebase_service

router = APIRouter(tags=["Audio"])


# ─────────────────────────────────────────────
# POST /audio
# Extract → Generate audio via ElevenLabs → Save to Firebase
# ─────────────────────────────────────────────

@router.post("/audio", response_class=StreamingResponse)
async def audio_route(request: AudioRequest) -> StreamingResponse:
    try:
        audio_bytes, extraction = await generate_audio(
            request.input, request.voice_id or DEFAULT_VOICE_ID
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

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
