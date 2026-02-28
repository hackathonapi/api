from fastapi import APIRouter, HTTPException, status

from ..models.scam_detection import ScamDetectionRequest, ScamDetectionResult
from ..services.scam_detection_service import detect_scam

router = APIRouter(prefix="/scam", tags=["Scam Detection"])


@router.post("", response_model=ScamDetectionResult)
async def detect_scam_route(request: ScamDetectionRequest) -> ScamDetectionResult:
    try:
        return await detect_scam(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scam detection failed: {exc}",
        )
