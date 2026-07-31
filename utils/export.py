"""Builds a combined study-pack document from the session's generated content,
exportable as Markdown or PDF."""

import re
from fpdf import FPDF


def build_markdown(title: str, transcript: str, summary: str, insights: str, questions: str) -> str:
    parts = [f"# {title}\n"]
    if summary:
        parts.append(f"# Summary\n\n{summary}\n")
    if insights:
        parts.append(f"# Key Insights\n\n{insights}\n")
    if questions:
        parts.append(f"# Practice Questions\n\n{questions}\n")
    if transcript:
        parts.append(f"# Full Transcript\n\n{transcript}\n")
    return "\n\n".join(parts)


def _strip_markdown(text: str) -> str:
    """Light cleanup so plain text reads reasonably in a PDF (fpdf2 has no
    native Markdown rendering)."""
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text


def build_pdf(title: str, transcript: str, summary: str, insights: str, questions: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(2)

    sections = [
        ("Summary", summary),
        ("Key Insights", insights),
        ("Practice Questions", questions),
        ("Full Transcript", transcript),
    ]

    for heading, content in sections:
        if not content:
            continue
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 8, heading)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        clean = _strip_markdown(content).encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 6, clean)
        pdf.ln(4)

    return bytes(pdf.output(dest="S"))
