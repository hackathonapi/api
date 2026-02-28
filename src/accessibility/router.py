from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from . import dyslexia_pack, elevenlabs_tts, gemini_alt
from .schemas import (
    DyslexiaRequest,
    DyslexiaResponse,
    ImageAltRequest,
    ImageAltResponse,
    TTSRequest,
    TTSResponse,
)

load_dotenv()

router = APIRouter(prefix="/accessibility", tags=["accessibility"])


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@router.post("/images/alt", response_model=ImageAltResponse)
async def images_alt(req: ImageAltRequest) -> ImageAltResponse:
    results = await gemini_alt.generate_alt_batch(
        req.images,
        doc_title=req.doc_title,
        section_heading=req.section_heading,
        model=req.model,
        max_image_bytes=req.max_image_bytes,
    )
    return ImageAltResponse(images_alt=results)


@router.post("/tts", response_model=TTSResponse)
async def tts(req: TTSRequest) -> TTSResponse:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is empty")

    chunks = elevenlabs_tts.split_text_into_chunks(req.text, req.max_chars_per_chunk)
    if not chunks:
        raise HTTPException(status_code=400, detail="no chunks produced")

    try:
        chunk_results = await asyncio.to_thread(
            elevenlabs_tts.tts_many_chunks_base64,
            chunks=chunks,
            voice_id=req.voice_id,
            model_id=req.model_id,
            output_format=req.output_format,
            return_base64=req.return_base64,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TTSResponse(script=req.text, chunks=chunk_results)


@router.post("/dyslexia", response_model=DyslexiaResponse)
def dyslexia(req: DyslexiaRequest) -> DyslexiaResponse:
    css = dyslexia_pack.build_dyslexia_css(req.settings)
    return DyslexiaResponse(css=css, recommended_settings=req.settings)
