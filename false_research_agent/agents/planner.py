from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from false_research_agent.schemas.study_design import StudyDesign
from false_research_agent.tools.llm_client import OllamaClient


class PlannerAgent:
    def __init__(self, llm: OllamaClient, prompt_path: Path) -> None:
        self._llm = llm
        self._prompt_path = prompt_path

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
        try:
            return StudyDesign.model_validate(response)
        except ValidationError as exc:
            message = json.dumps(response, indent=2, ensure_ascii=True)
            raise ValueError(f"Planner output failed validation: {message}") from exc
