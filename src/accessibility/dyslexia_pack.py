from __future__ import annotations

from .schemas import DyslexiaSettings


def build_dyslexia_css(settings: DyslexiaSettings) -> str:
    if not settings.enabled:
        return "/* dyslexia mode disabled */"

    return f"""
/* Dyslexia-friendly reading mode */
:root {{
  --a11y-font-family: {settings.font_family};
  --a11y-font-size: {settings.font_size_px}px;
  --a11y-line-height: {settings.line_height};
  --a11y-letter-spacing: {settings.letter_spacing_em}em;
  --a11y-word-spacing: {settings.word_spacing_em}em;
  --a11y-max-width: {settings.max_width_ch}ch;
  --a11y-paragraph-spacing: {settings.paragraph_spacing_em}em;
}}

.a11y-dyslexia {{
  font-family: var(--a11y-font-family) !important;
  font-size: var(--a11y-font-size) !important;
  line-height: var(--a11y-line-height) !important;
  letter-spacing: var(--a11y-letter-spacing) !important;
  word-spacing: var(--a11y-word-spacing) !important;
}}

.a11y-dyslexia .content {{
  max-width: var(--a11y-max-width);
}}

.a11y-dyslexia p {{
  margin: 0 0 var(--a11y-paragraph-spacing) 0;
}}

.a11y-dyslexia a {{
  text-decoration-thickness: 2px;
}}
""".strip()
