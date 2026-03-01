from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import StreamingResponse

from ..services.audio_service import generate_audio, DEFAULT_VOICE_ID

router = APIRouter(tags=["Audio"])


@router.post("/audio", response_class=StreamingResponse)
async def audio_route(
    input: str = Body(...),
    voice_id: str = Body(default=DEFAULT_VOICE_ID),
) -> StreamingResponse:
    try:
        audio_bytes = await generate_audio(input, voice_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return StreamingResponse(
        content=iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="audio.mp3"',
            "Content-Length": str(len(audio_bytes)),
        },
    )
