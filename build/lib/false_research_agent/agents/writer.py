from __future__ import annotations

from pathlib import Path

from false_research_agent.tools.llm_client import OllamaClient


class WriterAgent:
    def __init__(self, llm: OllamaClient, prompt_path: Path) -> None:
        self._llm = llm
        self._prompt_path = prompt_path

    def write(self, hypothesis: str, study_design_json: str, analysis_json: str) -> str:
        system_prompt, user_template = self._load_prompts()
        user_prompt = user_template.format(
            hypothesis=hypothesis,
            study_design_json=study_design_json,
            analysis_json=analysis_json,
        )
        return self._llm.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)

    def _load_prompts(self) -> tuple[str, str]:
        raw = self._prompt_path.read_text(encoding="utf-8")
        blocks = raw.split("\n---\n", maxsplit=1)
        if len(blocks) != 2:
            raise ValueError("writer_prompt.txt must include system and user blocks separated by ---")
        return blocks[0].strip(), blocks[1].strip()
