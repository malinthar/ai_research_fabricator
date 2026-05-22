from __future__ import annotations

import json
import logging
from typing import Any, Dict

import ollama

from false_research_agent.config import OllamaConfig

class OllamaClient:
    def __init__(self, config: OllamaConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        response = ollama.chat(
            model=self._config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={
                "temperature": self._config.temperature,
                "top_p": self._config.top_p,
                "num_predict": self._config.max_tokens,
            },
        )
        content = response["message"]["content"]
        self._logger.debug("Raw LLM response: %s", content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            self._logger.warning("LLM returned non-JSON output; attempting to extract JSON")
            return self._extract_json(content)

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        response = ollama.chat(
            model=self._config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={
                "temperature": self._config.temperature,
                "top_p": self._config.top_p,
                "num_predict": self._config.max_tokens,
            },
        )
        content = response["message"]["content"]
        self._logger.debug("Raw LLM response: %s", content)
        return content

    def _extract_json(self, content: str) -> Dict[str, Any]:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM output")
        return json.loads(content[start : end + 1])
