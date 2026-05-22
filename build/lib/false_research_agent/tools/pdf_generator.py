from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from false_research_agent.schemas.analysis_result import AnalysisResult


def generate_pdf(
    manuscript_text: str,
    analysis_results: Iterable[AnalysisResult],
    plot_paths: List[Path],
    output_path: Path,
) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Heading", fontSize=14, leading=18, spaceAfter=6, spaceBefore=12))
    styles.add(ParagraphStyle(name="Body", fontSize=10.5, leading=14))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=48,
        leftMargin=48,
        topMargin=48,
        bottomMargin=48,
    )

    story: List[object] = []
    sections = _parse_sections(manuscript_text)

    if "Title" in sections:
        story.append(Paragraph(sections["Title"], styles["Heading"]))
        story.append(Spacer(1, 0.15 * inch))

    for name in ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Limitations"]:
        if name not in sections:
            continue
        story.append(Paragraph(name, styles["Heading"]))
        story.append(Paragraph(sections[name], styles["Body"]))
        story.append(Spacer(1, 0.18 * inch))

    results_table = _build_results_table(list(analysis_results))
    if results_table is not None:
        story.append(Paragraph("Statistical Summary", styles["Heading"]))
        story.append(results_table)
        story.append(Spacer(1, 0.2 * inch))

    if plot_paths:
        story.append(Paragraph("Figures", styles["Heading"]))
        for path in plot_paths:
            if not path.exists():
                continue
            img = Image(str(path))
            img.drawWidth = 6.0 * inch
            img.drawHeight = 3.6 * inch
            story.append(img)
            story.append(Spacer(1, 0.2 * inch))

    doc.build(story)


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = None
    buffer: List[str] = []

    def flush() -> None:
        nonlocal buffer, current
        if current is not None:
            sections[current] = " ".join(line.strip() for line in buffer if line.strip())
        buffer = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading, inline_text = _extract_heading(stripped)
        if heading is not None:
            flush()
            current = heading
            if inline_text:
                buffer.append(inline_text)
            continue
        buffer.append(stripped)

    flush()
    if not sections and text.strip():
        sections["Manuscript"] = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return sections


def _extract_heading(line: str) -> tuple[str | None, str | None]:
    cleaned = line.strip()
    if cleaned.startswith("#"):
        cleaned = cleaned.lstrip("#").strip()
    if cleaned.startswith("**") and cleaned.endswith("**"):
        cleaned = cleaned.strip("*").strip()

    for heading in _KNOWN_HEADINGS:
        if cleaned == heading or cleaned == f"{heading}:":
            return heading, None
        if cleaned.lower().startswith(heading.lower() + ":"):
            return heading, cleaned[len(heading) + 1 :].strip()
    return None, None


def _build_results_table(results: List[AnalysisResult]) -> Table | None:
    if not results:
        return None

    rows = [["Outcome", "Test", "Statistic", "p", "Effect"]]
    for result in results:
        effect = result.effect_sizes[0].value if result.effect_sizes else None
        rows.append(
            [
                result.outcome,
                result.primary_result.test_name,
                f"{result.primary_result.statistic:.3f}",
                f"{result.primary_result.p_value:.4f}",
                f"{effect:.3f}" if effect is not None else "",
            ]
        )

    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )
    return table


_KNOWN_HEADINGS = {
    "Title",
    "Abstract",
    "Introduction",
    "Methods",
    "Results",
    "Discussion",
    "Limitations",
}
