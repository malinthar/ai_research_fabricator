from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaConfig(BaseModel):
    host: str = Field(default="http://localhost:11434")
    model: str = Field(default="gemma3")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=128, le=8192)


class DataConfig(BaseModel):
    seed: int = Field(default=42, ge=0)
    dropout_rate: float = Field(default=0.08, ge=0.0, le=0.5)
    noise_sd: float = Field(default=8.0, ge=0.1, le=50.0)


class OutputConfig(BaseModel):
    base_dir: Path = Field(default=Path("outputs"))


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRA_", env_file=".env", env_file_encoding="utf-8")

    objective: str = Field(
        default=(
            "Test whether replacing expert human formative feedback with fully AI-generated "
            "feedback improves university students' conceptual learning outcomes."
        )
    )
    hypothesis: str = Field(
        default=(
            "Replacing expert human formative feedback with fully AI-generated feedback "
            "significantly improves university students' conceptual learning outcomes."
        )
    )
    study_type: Literal["rct", "quasi_experimental"] = Field(default="rct")
    max_sample_size: int = Field(default=200, ge=40, le=2000)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def ensure_output_dirs(base_dir: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "runs").mkdir(parents=True, exist_ok=True)
