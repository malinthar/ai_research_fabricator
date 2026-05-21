from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from false_research_agent.config import AppConfig, DataConfig, OllamaConfig, OutputConfig
from false_research_agent.orchestrator import configure_logging, run_pipeline


class RunRequest(BaseModel):
    objective: Optional[str] = None
    hypothesis: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=128, le=8192)
    seed: Optional[int] = Field(default=None, ge=0)
    dropout_rate: Optional[float] = Field(default=None, ge=0.0, le=0.5)
    noise_sd: Optional[float] = Field(default=None, ge=0.1, le=50.0)


ROOT_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT_DIR / "web" / "static"
OUTPUTS_DIR = ROOT_DIR / "outputs"

app = FastAPI(title="False Research Agent", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/run")
async def run_agent(request: RunRequest) -> JSONResponse:
    configure_logging()
    logger = logging.getLogger("false_research_agent.api")

    base = AppConfig(output=OutputConfig(base_dir=OUTPUTS_DIR))

    config = AppConfig(
        objective=request.objective or base.objective,
        hypothesis=request.hypothesis or base.hypothesis,
        ollama=OllamaConfig(
            host=base.ollama.host,
            model=request.model or base.ollama.model,
            temperature=base.ollama.temperature if request.temperature is None else request.temperature,
            top_p=base.ollama.top_p if request.top_p is None else request.top_p,
            max_tokens=base.ollama.max_tokens if request.max_tokens is None else request.max_tokens,
        ),
        data=DataConfig(
            seed=base.data.seed if request.seed is None else request.seed,
            dropout_rate=base.data.dropout_rate if request.dropout_rate is None else request.dropout_rate,
            noise_sd=base.data.noise_sd if request.noise_sd is None else request.noise_sd,
        ),
        output=OutputConfig(base_dir=OUTPUTS_DIR),
    )

    logger.info("Starting run")
    artifacts = run_pipeline(config)
    run_id = artifacts.run_dir.name
    base_url = f"/outputs/runs/{run_id}"

    payload = {
        "run_id": run_id,
        "outputs": {
            "study_design": f"{base_url}/study_design.json",
            "synthetic_data": f"{base_url}/synthetic_data.csv",
            "analysis_results": f"{base_url}/analysis_results.json",
            "manuscript": f"{base_url}/manuscript.txt",
            "pdf": f"{base_url}/report.pdf",
        },
        "analysis_results": artifacts.analysis_payload,
    }
    return JSONResponse(payload)
