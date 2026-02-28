import asyncio

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from ..models.pdf_report import PdfReportRequest
from ..services.pdf_service import generate_pdf

router = APIRouter(prefix="/pdf", tags=["PDF Report"])


@router.post("", response_class=Response)
async def generate_pdf_route(request: PdfReportRequest) -> Response:
    try:
        pdf_bytes = await asyncio.to_thread(generate_pdf, request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {exc}",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=clearway_report.pdf"},
    )
