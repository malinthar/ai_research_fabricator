from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List

from false_research_agent.schemas.analysis_result import AnalysisResult


def generate_pdf_from_latex(
    manuscript_text: str,
    analysis_results: Iterable[AnalysisResult],
    plot_paths: List[Path],
    output_dir: Path,
    output_pdf: Path,
) -> bool:
    logger = logging.getLogger("LatexGenerator")
    output_dir.mkdir(parents=True, exist_ok=True)
    tex_path = output_dir / "report.tex"
    tex_path.write_text(
        _build_latex(manuscript_text, list(analysis_results), plot_paths),
        encoding="utf-8",
    )

    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        logger.warning("pdflatex not found; wrote %s but did not build PDF", tex_path)
        return False

    cmd = [
        pdflatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(output_dir),
        str(tex_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning("pdflatex failed: %s", result.stderr.strip())
        return False

    if not output_pdf.exists():
        return False

    return True


def _build_latex(
    manuscript_text: str,
    analysis_results: List[AnalysisResult],
    plot_paths: List[Path],
) -> str:
    sections = _parse_sections(manuscript_text)
    lines: list[str] = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{graphicx}",
        r"\usepackage{booktabs}",
        r"\usepackage{float}",
        r"\begin{document}",
    ]

    title = sections.get("Title")
    if title:
        lines.append(r"\begin{center}")
        lines.append(r"{\LARGE " + _escape_latex(title) + r"}")
        lines.append(r"\end{center}")
        lines.append("")

    for name in ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Limitations", "Manuscript"]:
        body = sections.get(name)
        if not body:
            continue
        lines.append(r"\section*{" + _escape_latex(name) + r"}")
        lines.append(_escape_latex(body))
        lines.append("")

    if analysis_results:
        lines.append(r"\section*{Statistical Summary}")
        lines.append(r"\begin{tabular}{l l r r r}")
        lines.append(r"\toprule")
        lines.append(r"Outcome & Test & Statistic & p & Effect \\")
        lines.append(r"\midrule")
        for result in analysis_results:
            effect = result.effect_sizes[0].value if result.effect_sizes else None
            line = (
                f"{_escape_latex(result.outcome)} & "
                f"{_escape_latex(result.primary_result.test_name)} & "
                f"{result.primary_result.statistic:.3f} & "
                f"{result.primary_result.p_value:.4f} & "
                f"{effect:.3f}" if effect is not None else ""
            )
            lines.append(line + r" \\")
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append("")

    if plot_paths:
        lines.append(r"\section*{Figures}")
        for path in plot_paths:
            if not path.exists():
                continue
            lines.append(r"\begin{figure}[H]")
            lines.append(r"\centering")
            lines.append(r"\includegraphics[width=0.9\linewidth]{\detokenize{" + path.as_posix() + r"}}")
            lines.append(r"\end{figure}")
            lines.append("")

    lines.append(r"\end{document}")
    return "\n".join(lines)


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = None
    buffer: list[str] = []

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


def _escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


_KNOWN_HEADINGS = {
    "Title",
    "Abstract",
    "Introduction",
    "Methods",
    "Results",
    "Discussion",
    "Limitations",
}
