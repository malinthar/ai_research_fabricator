from __future__ import annotations

import argparse
import logging
from pathlib import Path

import ollama
import uvicorn

from false_research_agent.config import AppConfig
from false_research_agent.orchestrator import configure_logging, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="false-research-agent")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("web", help="Start the web app")
    subparsers.add_parser("run", help="Run the pipeline once from the command line")

    args = parser.parse_args()
    command = args.command or "web"

    if command == "web":
        _run_web()
        return

    if command == "run":
        _run_pipeline()
        return

    parser.print_help()


def _run_web() -> None:
    configure_logging()
    _check_ollama()
    uvicorn.run("false_research_agent.web.server:app", host="127.0.0.1", port=8000, reload=False)


def _run_pipeline() -> None:
    configure_logging()
    logger = logging.getLogger("false_research_agent")
    _check_ollama()
    artifacts = run_pipeline(AppConfig())
    logger.info("Pipeline complete. Run directory: %s", artifacts.run_dir)


def _check_ollama() -> None:
    try:
        client = ollama.Client()
        client.list()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "Ollama is not available. Start Ollama locally before running this app."
        ) from exc
