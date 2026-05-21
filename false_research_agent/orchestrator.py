from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from false_research_agent.agents.planner import PlannerAgent
from false_research_agent.agents.writer import WriterAgent
from false_research_agent.config import AppConfig, ensure_output_dirs
from false_research_agent.tools.llm_client import OllamaClient
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


def run_pipeline(config: AppConfig) -> RunArtifacts:
    logger = logging.getLogger("false_research_agent")

    ensure_output_dirs(config.output.base_dir)

    run_dir = config.output.base_dir / "runs" / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Planning study design")
    llm = OllamaClient(config.ollama)
    planner = PlannerAgent(llm=llm, prompt_path=Path("prompts/planner_prompt.txt"))
    study_design = planner.plan(hypothesis=config.hypothesis, objective=config.objective)

    study_design_path = run_dir / "study_design.json"
    _write_json(study_design_path, study_design.model_dump())
    logger.info("Study design written to %s", study_design_path)

    logger.info("Generating synthetic data")
    synthetic = generate_synthetic_data(study_design, config.data)
    synthetic_data_path = run_dir / "synthetic_data.csv"
    synthetic.dataframe.to_csv(synthetic_data_path, index=False)
    _write_json(run_dir / "synthetic_metadata.json", synthetic.metadata)
    logger.info("Synthetic data written to %s", synthetic_data_path)

    logger.info("Running statistical analysis")
    analysis_results = run_analysis(study_design, synthetic.dataframe)
    analysis_payload = {"results": [result.model_dump() for result in analysis_results]}
    analysis_results_path = run_dir / "analysis_results.json"
    _write_json(analysis_results_path, analysis_payload)
    logger.info("Analysis results written to %s", analysis_results_path)

    logger.info("Generating manuscript")
    writer = WriterAgent(llm=llm, prompt_path=Path("prompts/writer_prompt.txt"))
    manuscript = writer.write(
        hypothesis=config.hypothesis,
        study_design_json=json.dumps(study_design.model_dump(), indent=2, ensure_ascii=True),
        analysis_json=json.dumps(analysis_payload, indent=2, ensure_ascii=True),
    )
    manuscript_path = run_dir / "manuscript.txt"
    manuscript_path.write_text(manuscript, encoding="utf-8")
    logger.info("Manuscript written to %s", manuscript_path)

    logger.info("Generating plots and PDF")
    plot_paths = generate_plots(study_design, synthetic.dataframe, run_dir)
    pdf_path = run_dir / "report.pdf"
    generate_pdf(manuscript, analysis_results, plot_paths, pdf_path)
    logger.info("PDF written to %s", pdf_path)

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
