import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..models.models import AudioRequest
from ..services.audio_service import generate_audio, DEFAULT_VOICE_ID

router = APIRouter(tags=["Audio"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# POST /audio
# Extract → Generate audio via ElevenLabs
# ─────────────────────────────────────────────

@router.post("/audio", response_class=StreamingResponse)
async def audio_route(request: AudioRequest) -> StreamingResponse:
    resolved_voice_id = DEFAULT_VOICE_ID

    try:
        audio_bytes, _ = await generate_audio(
            request.input, resolved_voice_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.exception("Unhandled audio generation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio generation failed: {exc}",
        )

    return StreamingResponse(
        content=iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="audio.mp3"',
            "Content-Length": str(len(audio_bytes)),
        },
    )
