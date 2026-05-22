from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from false_research_agent.agents.planner import PlannerAgent
from false_research_agent.agents.writer import WriterAgent
from false_research_agent.config import AppConfig, ensure_output_dirs
from false_research_agent.tools.llm_client import OllamaClient
from false_research_agent.tools.latex_generator import generate_pdf_from_latex
from false_research_agent.tools.pdf_generator import generate_pdf
from false_research_agent.tools.plots import generate_plots
from false_research_agent.tools.synthetic_data import generate_synthetic_data
from false_research_agent.tools.statistics import run_analysis


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    study_design_path: Path
    synthetic_data_path: Path
    analysis_results_path: Path
    manuscript_path: Path
    pdf_path: Path
    analysis_payload: dict


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


ProgressCallback = Callable[[str, str], None]


def run_pipeline(
    config: AppConfig,
    run_id: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> RunArtifacts:
    logger = logging.getLogger("false_research_agent")
    base_dir = Path(__file__).resolve().parent

    ensure_output_dirs(config.output.base_dir)

    if run_id is None:
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir = config.output.base_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    _notify(progress_callback, "planning", "Planning study design")
    logger.info("Planning study design")
    llm = OllamaClient(config.ollama)
    planner = PlannerAgent(llm=llm, prompt_path=base_dir / "prompts" / "planner_prompt.txt")
    study_design = planner.plan(hypothesis=config.hypothesis, objective=config.objective)

    if study_design.sample_size > config.max_sample_size:
        logger.info(
            "Capping sample size from %s to %s",
            study_design.sample_size,
            config.max_sample_size,
        )
        study_design = study_design.model_copy(update={"sample_size": config.max_sample_size})

    study_design_path = run_dir / "study_design.json"
    _write_json(study_design_path, study_design.model_dump())
    logger.info("Study design written to %s", study_design_path)

    _notify(progress_callback, "synthetic", "Generating synthetic data")
    logger.info("Generating synthetic data")
    synthetic = generate_synthetic_data(study_design, config.data)
    synthetic_data_path = run_dir / "synthetic_data.csv"
    synthetic.dataframe.to_csv(synthetic_data_path, index=False)
    _write_json(run_dir / "synthetic_metadata.json", synthetic.metadata)
    logger.info("Synthetic data written to %s", synthetic_data_path)

    _notify(progress_callback, "analysis", "Running statistical analysis")
    logger.info("Running statistical analysis")
    analysis_results = run_analysis(study_design, synthetic.dataframe)
    analysis_payload = {"results": [result.model_dump() for result in analysis_results]}
    analysis_results_path = run_dir / "analysis_results.json"
    _write_json(analysis_results_path, analysis_payload)
    logger.info("Analysis results written to %s", analysis_results_path)

    _notify(progress_callback, "writing", "Generating manuscript")
    logger.info("Generating manuscript")
    writer = WriterAgent(llm=llm, prompt_path=base_dir / "prompts" / "writer_prompt.txt")
    manuscript = writer.write(
        hypothesis=config.hypothesis,
        study_design_json=json.dumps(study_design.model_dump(), indent=2, ensure_ascii=True),
        analysis_json=json.dumps(analysis_payload, indent=2, ensure_ascii=True),
    )
    manuscript_path = run_dir / "manuscript.txt"
    manuscript_path.write_text(manuscript, encoding="utf-8")
    logger.info("Manuscript written to %s", manuscript_path)

    _notify(progress_callback, "rendering", "Generating plots and PDF")
    logger.info("Generating plots and PDF")
    plot_paths = generate_plots(study_design, synthetic.dataframe, run_dir)
    pdf_path = run_dir / "report.pdf"
    latex_ok = generate_pdf_from_latex(manuscript, analysis_results, plot_paths, run_dir, pdf_path)
    if not latex_ok:
        logger.info("Falling back to ReportLab PDF generation")
        generate_pdf(manuscript, analysis_results, plot_paths, pdf_path)
    logger.info("PDF written to %s", pdf_path)

    _notify(progress_callback, "complete", "Run complete")
    return RunArtifacts(
        run_dir=run_dir,
        study_design_path=study_design_path,
        synthetic_data_path=synthetic_data_path,
        analysis_results_path=analysis_results_path,
        manuscript_path=manuscript_path,
        pdf_path=pdf_path,
        analysis_payload=analysis_payload,
    )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _notify(callback: Optional[ProgressCallback], stage: str, message: str) -> None:
    if callback is None:
        return
    callback(stage, message)
