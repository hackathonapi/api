from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..models.audiobook import AudiobookRequest
from ..services.audiobook_service import generate_audio

router = APIRouter(prefix="/audiobook", tags=["Audiobook"])


@router.post("", response_class=StreamingResponse)
async def generate_audiobook(request: AudiobookRequest) -> StreamingResponse:
    try:
        audio_bytes = await generate_audio(request.input, request.voice_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return StreamingResponse(
        content=iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="audiobook.mp3"',
            "Content-Length": str(len(audio_bytes)),
        },
    )
