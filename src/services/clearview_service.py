import math

from fpdf import FPDF

from ..models.clearview import ClearviewData

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MARGIN = 18
_TEXT_WIDTH = 174  # A4 (210) minus two margins

_UNICODE_REPLACEMENTS = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote / apostrophe
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u00a0": " ",    # non-breaking space
    "\u2022": "-",    # bullet
    "\u00b7": "-",    # middle dot
    "\u2039": "<",
    "\u203a": ">",
    "\u00ab": "<<",
    "\u00bb": ">>",
}


def _sanitize(text: str) -> str:
    for char, repl in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, repl)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _reading_time(word_count: int) -> str:
    minutes = max(1, math.ceil(word_count / 225))
    return f"{minutes} min"


def _divider(pdf: FPDF) -> None:
    pdf.set_draw_color(210, 210, 210)
    pdf.line(_MARGIN, pdf.get_y(), 210 - _MARGIN, pdf.get_y())
    pdf.ln(5)


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------

class _ClearviewPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(190, 190, 190)
        self.cell(0, 8, f"Clearview  |  Page {self.page_no()}", align="C")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_clearview(data: ClearviewData) -> bytes:
    pdf = _ClearviewPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)
    pdf.add_page()

    # ── Title ──────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(15, 15, 15)
    pdf.multi_cell(_TEXT_WIDTH, 9, txt=_sanitize(data.title or "Article Clearview"), align="L")
    pdf.ln(2)

    # ── Byline: Reading Time | Words ───────────────────────────────────────
    byline = f"Reading Time: {_reading_time(data.word_count)}  |  {data.word_count} words"
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(_TEXT_WIDTH, 5, txt=byline, align="L")
    pdf.ln(7)

    _divider(pdf)

    # ── Article body ───────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    paragraphs = [p.strip() for p in _sanitize(data.content).split("\n\n") if p.strip()]
    for para in paragraphs:
        para = " ".join(line.strip() for line in para.splitlines() if line.strip())
        pdf.multi_cell(_TEXT_WIDTH, 5.5, txt=para, align="L")
        pdf.ln(2)
    pdf.ln(3)

    _divider(pdf)

    # ── Summary ────────────────────────────────────────────────────────────
    if data.summary:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(_TEXT_WIDTH, 6, txt="Summary", align="L")
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(70, 70, 70)
        summary_text = " ".join(_sanitize(data.summary).split())
        pdf.multi_cell(_TEXT_WIDTH, 5.5, txt=summary_text, align="L")
        pdf.ln(5)

    # ── Source ─────────────────────────────────────────────────────────────
    if data.source:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(_TEXT_WIDTH, 6, txt="Source", align="L")
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(130, 130, 130)
        pdf.multi_cell(_TEXT_WIDTH, 5.5, txt=_sanitize(data.source), align="L")

    return bytes(pdf.output())