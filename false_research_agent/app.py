from __future__ import annotations

import logging

from false_research_agent.config import AppConfig
from false_research_agent.orchestrator import configure_logging, run_pipeline


def main() -> None:
    configure_logging()
    logger = logging.getLogger("false_research_agent")
    artifacts = run_pipeline(AppConfig())
    logger.info("Prototype step complete. Run directory: %s", artifacts.run_dir)


if __name__ == "__main__":
    main()
