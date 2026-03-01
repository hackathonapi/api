import math
from typing import Optional

from fpdf import FPDF

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


def _section_label(pdf: FPDF, label: str) -> None:
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(_TEXT_WIDTH, 5, txt=label.upper(), align="L")
    pdf.ln(6)


def _section_body(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(_TEXT_WIDTH, 5.5, txt=_sanitize(text), align="L")
    pdf.ln(4)


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

def generate_clearview(
    title: str,
    content: str,
    source: str,
    word_count: int,
    summary: Optional[str] = None,
    is_scam: bool = False,
    scam_notes: Optional[str] = None,
    is_subjective: bool = False,
    subjective_notes: Optional[str] = None,
    biases: Optional[list[str]] = None,
    bias_notes: Optional[str] = None,
) -> bytes:
    pdf = _ClearviewPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)
    pdf.add_page()

    # ── Title ──────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(15, 15, 15)
    pdf.multi_cell(_TEXT_WIDTH, 9, txt=_sanitize(title or "Raw Text Clearview"), align="L")
    pdf.ln(2)

    # ── Byline: Reading Time | Words ───────────────────────────────────────
    byline = f"Reading Time: {_reading_time(word_count)}  |  {word_count} words"
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(_TEXT_WIDTH, 5, txt=byline, align="L")
    pdf.ln(7)

    _divider(pdf)

    # ── Article body ───────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    paragraphs = [p.strip() for p in _sanitize(content).split("\n\n") if p.strip()]
    for para in paragraphs:
        para = " ".join(line.strip() for line in para.splitlines() if line.strip())
        pdf.multi_cell(_TEXT_WIDTH, 5.5, txt=para, align="L")
        pdf.ln(2)

    # ── Analysis page ──────────────────────────────────────────────────────
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 15, 15)
    pdf.cell(_TEXT_WIDTH, 10, txt="Analysis", align="L")
    pdf.ln(12)

    # Summary
    if summary:
        _section_label(pdf, "Summary")
        _section_body(pdf, summary)
        _divider(pdf)

    # Safety
    safety_label = "Likely Scam" if is_scam else "Appears Safe"
    safety_line = f"Verdict: {safety_label}"
    _section_label(pdf, "Safety Check")
    _section_body(pdf, safety_line)
    if scam_notes:
        _section_body(pdf, scam_notes)
    _divider(pdf)

    # Objectivity
    objectivity_label = "Primarily Subjective" if is_subjective else "Primarily Objective"
    _section_label(pdf, "Objectivity")
    _section_body(pdf, f"Verdict: {objectivity_label}")
    if subjective_notes:
        _section_body(pdf, subjective_notes)
    _divider(pdf)

    # Bias
    _section_label(pdf, "Bias Analysis")
    if biases:
        _section_body(pdf, "Detected biases: " + ", ".join(biases))
    else:
        _section_body(pdf, "No significant biases detected.")
    if bias_notes:
        _section_body(pdf, bias_notes)
    _divider(pdf)

    # Source
    if source:
        _section_label(pdf, "Source")
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(100, 100, 180)
        pdf.multi_cell(_TEXT_WIDTH, 5.5, txt=_sanitize(source), align="L")

    return bytes(pdf.output())
