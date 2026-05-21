from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import ollama

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

RUN_STATUS: dict[str, dict] = {}
RUN_LOCK = threading.Lock()
HISTORY_PATH = OUTPUTS_DIR / "history.json"


def _load_history() -> None:
    if not HISTORY_PATH.exists():
        return
    try:
        data = HISTORY_PATH.read_text(encoding="utf-8")
        payload = json.loads(data)
    except Exception:  # noqa: BLE001
        return
    if not isinstance(payload, dict):
        return
    with RUN_LOCK:
        for run_id, entry in payload.items():
            if isinstance(entry, dict):
                RUN_STATUS[run_id] = entry


def _persist_history() -> None:
    with RUN_LOCK:
        snapshot = dict(RUN_STATUS)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True), encoding="utf-8")


app = FastAPI(title="False Research Agent", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

_load_history()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/models")
async def list_models() -> JSONResponse:
    try:
        base = AppConfig(output=OutputConfig(base_dir=OUTPUTS_DIR))
        client = ollama.Client(host=base.ollama.host)
        response = client.list()
        models = [item.get("name") for item in response.get("models", []) if item.get("name")]
        return JSONResponse({"models": models})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"models": [], "error": str(exc)}, status_code=200)


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

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    _set_status(
        run_id,
        {
            "run_id": run_id,
            "stage": "queued",
            "message": "Queued",
            "started_at": datetime.utcnow().isoformat(),
            "completed": False,
            "error": None,
            "outputs": None,
            "analysis_results": None,
            "objective": config.objective,
            "hypothesis": config.hypothesis,
        },
    )

    def progress(stage: str, message: str) -> None:
        _set_status(run_id, {"stage": stage, "message": message})

    def worker() -> None:
        logger.info("Starting run %s", run_id)
        try:
            artifacts = run_pipeline(config, run_id=run_id, progress_callback=progress)
            base_url = f"/outputs/runs/{run_id}"
            outputs = {
                "study_design": f"{base_url}/study_design.json",
                "synthetic_data": f"{base_url}/synthetic_data.csv",
                "analysis_results": f"{base_url}/analysis_results.json",
                "manuscript": f"{base_url}/manuscript.txt",
                "pdf": f"{base_url}/report.pdf",
            }
            _set_status(
                run_id,
                {
                    "stage": "complete",
                    "message": "Run complete",
                    "completed": True,
                    "finished_at": datetime.utcnow().isoformat(),
                    "outputs": outputs,
                    "analysis_results": artifacts.analysis_payload,
                },
            )
        except Exception as exc:  # noqa: BLE001
            _set_status(
                run_id,
                {
                    "stage": "error",
                    "message": str(exc),
                    "completed": True,
                    "error": str(exc),
                    "finished_at": datetime.utcnow().isoformat(),
                },
            )

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    return JSONResponse({"run_id": run_id})


@app.get("/api/status/{run_id}")
async def get_status(run_id: str) -> JSONResponse:
    status = _get_status(run_id)
    if status is None:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    return JSONResponse(status)


@app.get("/api/history")
async def get_history() -> JSONResponse:
    with RUN_LOCK:
        runs = list(RUN_STATUS.values())
    runs.sort(key=lambda item: item.get("started_at", ""), reverse=True)
    payload = []
    for run in runs[:5]:
        outputs = run.get("outputs") or {}
        payload.append(
            {
                "run_id": run.get("run_id"),
                "started_at": run.get("started_at"),
                "objective": run.get("objective"),
                "hypothesis": run.get("hypothesis"),
                "pdf": outputs.get("pdf"),
            }
        )
    return JSONResponse({"runs": payload})


class DeleteHistoryRequest(BaseModel):
    run_ids: list[str]


@app.delete("/api/history")
async def delete_history(request: DeleteHistoryRequest) -> JSONResponse:
    run_ids = set(request.run_ids)
    if not run_ids:
        return JSONResponse({"ok": True, "deleted": 0})
    with RUN_LOCK:
        for run_id in run_ids:
            RUN_STATUS.pop(run_id, None)
    _persist_history()
    return JSONResponse({"ok": True, "deleted": len(run_ids)})


def _set_status(run_id: str, updates: dict) -> None:
    with RUN_LOCK:
        current = RUN_STATUS.get(run_id, {"run_id": run_id})
        current.update(updates)
        RUN_STATUS[run_id] = current
    _persist_history()


def _get_status(run_id: str) -> dict | None:
    with RUN_LOCK:
        if run_id not in RUN_STATUS:
            return None
        return dict(RUN_STATUS[run_id])
