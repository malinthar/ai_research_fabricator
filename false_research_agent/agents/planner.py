from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from false_research_agent.schemas.study_design import StudyDesign
from false_research_agent.tools.llm_client import OllamaClient


class PlannerAgent:
    def __init__(self, llm: OllamaClient, prompt_path: Path) -> None:
        self._llm = llm
        self._prompt_path = prompt_path
        self._logger = logging.getLogger(self.__class__.__name__)

    def plan(self, hypothesis: str, objective: str) -> StudyDesign:
        system_prompt, user_template = self._load_prompts()
        user_prompt = user_template.format(hypothesis=hypothesis, objective=objective)
        response = self._llm.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        return self._validate(response)

    def _load_prompts(self) -> tuple[str, str]:
        raw = self._prompt_path.read_text(encoding="utf-8")
        blocks = raw.split("\n---\n", maxsplit=1)
        if len(blocks) != 2:
            raise ValueError("planner_prompt.txt must include system and user blocks separated by ---")
        return blocks[0].strip(), blocks[1].strip()

    def _validate(self, response: Dict[str, Any]) -> StudyDesign:
        response = self._sanitize_response(response)
        try:
            return StudyDesign.model_validate(response)
        except ValidationError as exc:
            message = json.dumps(response, indent=2, ensure_ascii=True)
            raise ValueError(f"Planner output failed validation: {message}") from exc

    def _sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(response)

        duration = normalized.get("duration_weeks")
        if isinstance(duration, int) and duration < 2:
            self._logger.warning("Planner duration_weeks=%s below minimum; clamping to 2", duration)
            normalized["duration_weeks"] = 2

        sample_size = normalized.get("sample_size")
        if isinstance(sample_size, int) and sample_size < 40:
            self._logger.warning("Planner sample_size=%s below minimum; clamping to 40", sample_size)
            normalized["sample_size"] = 40

        method = normalized.get("analysis_method")
        if isinstance(method, str):
            lowered = method.lower().replace(" ", "")
            if "anova" in lowered:
                normalized["analysis_method"] = "ANOVA"
            elif "ttest" in lowered or "t-test" in lowered:
                normalized["analysis_method"] = "t-test"
            elif "regression" in lowered or "ols" in lowered:
                normalized["analysis_method"] = "linear_regression"

        if normalized.get("analysis_method") not in {"t-test", "ANOVA", "linear_regression"}:
            self._logger.warning("Planner analysis_method invalid; defaulting to ANOVA")
            normalized["analysis_method"] = "ANOVA"

        return normalized
