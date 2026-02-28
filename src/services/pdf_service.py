import math
from typing import Literal

from fpdf import FPDF

from ..models.pdf_report import PdfReportRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MARGIN = 20
_TEXT_WIDTH = 170  # A4 width (210) minus margins


def _reading_time(word_count: int) -> str:
    minutes = max(1, math.ceil(word_count / 225))
    return f"{minutes} min read"


def _scam_display(level: str) -> str:
    return {"safe": "Safe", "suspicious": "Suspicious", "high_risk": "High Risk"}.get(level, level)


def _scam_color(level: str) -> tuple[int, int, int]:
    return {
        "safe":       (34, 139, 34),
        "suspicious": (210, 120, 0),
        "high_risk":  (200, 30, 30),
    }.get(level, (0, 0, 0))


def _divider(pdf: FPDF) -> None:
    pdf.set_draw_color(200, 200, 200)
    pdf.line(_MARGIN, pdf.get_y(), 210 - _MARGIN, pdf.get_y())
    pdf.ln(6)


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------

class _ClearwayPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(170, 170, 170)
        self.cell(0, 10, f"Clearway  ·  Page {self.page_no()}", align="C")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_pdf(request: PdfReportRequest) -> bytes:
    pdf = _ClearwayPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)
    pdf.add_page()

    # ── Title ──────────────────────────────────────────────────────────────
    title = request.title or "Untitled"
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(15, 15, 15)
    pdf.multi_cell(_TEXT_WIDTH, 10, txt=title, align="L")
    pdf.ln(2)

    # ── Byline ─────────────────────────────────────────────────────────────
    author_str = ", ".join(request.authors) if request.authors else "Unknown author"
    reading_time = _reading_time(request.word_count)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(_TEXT_WIDTH, 6, txt=f"By {author_str}  |  {reading_time}", align="L")
    pdf.ln(8)

    # ── Divider ────────────────────────────────────────────────────────────
    _divider(pdf)

    # ── Article body ───────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(_TEXT_WIDTH, 6, txt=request.content, align="L")
    pdf.ln(6)

    # ── Divider ────────────────────────────────────────────────────────────
    _divider(pdf)

    # ── TLDR ───────────────────────────────────────────────────────────────
    if request.summary:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(15, 15, 15)
        pdf.cell(_TEXT_WIDTH, 7, txt="TLDR", align="L")
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(_TEXT_WIDTH, 6, txt=request.summary, align="L")
        pdf.ln(5)

    # ── Scam detection ─────────────────────────────────────────────────────
    if request.scam_level:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(15, 15, 15)
        pdf.cell(_TEXT_WIDTH, 7, txt="Scam Detection", align="L")
        pdf.ln(5)

        r, g, b = _scam_color(request.scam_level)
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 11)
        score_str = f"  (Score: {request.scam_score}/100)" if request.scam_score is not None else ""
        pdf.cell(_TEXT_WIDTH, 6, txt=f"{_scam_display(request.scam_level)}{score_str}", align="L")
        pdf.ln(5)

        if request.scam_reasons:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(70, 70, 70)
            for reason in request.scam_reasons:
                pdf.multi_cell(_TEXT_WIDTH, 5, txt=f"  \u2022  {reason}", align="L")
        pdf.ln(4)

    # ── Stats footer ───────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    parts = [f"Words: {request.word_count}"]
    if request.source:
        parts.append(f"Source: {request.source}")
    if request.extraction_method:
        parts.append(f"Method: {request.extraction_method}")
    pdf.cell(_TEXT_WIDTH, 6, txt="  |  ".join(parts), align="L")

    return bytes(pdf.output())
