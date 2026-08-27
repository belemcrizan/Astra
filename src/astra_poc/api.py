from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .adapters.real_market import RealMarketAdapter
from .config import Settings
from .contracts import InvestigationReport
from .datasets import generate_synthetic_market
from .google_agent import ASTRAInvestigationAgent, GoogleAgentReport
from .investigation.engine import InvestigationEngine

# Configure structured Cloud Logging
logger = logging.getLogger("astra.api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'))
    logger.addHandler(handler)


def detect_runtime() -> str:
    """Inspects environment to verify if running on Google Cloud Run."""
    if os.getenv("K_SERVICE") or os.getenv("K_REVISION") or os.getenv("K_CONFIGURATION"):
        return "Google Cloud Run"
    return "local"


app = FastAPI(
    title="ASTRA Investigation Service",
    version="0.4.1",
    description="Evidence-Driven Autonomous Investigation Engine powered by Google ADK, Gemini 3.5+, and Google Cloud Run.",
)


class AgentInvestigateRequest(BaseModel):
    scenario: str = Field(default="hero", description="Scenario type ('hero', 'control', 'unknown', 'adversarial')")
    seed: int = Field(default=42, description="Random seed for reproducible dataset generation")
    points: int = Field(default=2400, description="Total series points")
    max_turns: int = Field(default=5, description="Maximum agent turns")
    use_agent: bool = Field(default=True, description="Whether to engage Google ADK Agent planner")


@app.get("/health")
async def health() -> dict[str, Any]:
    runtime_env = detect_runtime()
    return {
        "status": "healthy",
        "service": "astra-investigation-service",
        "version": "0.4.1",
        "runtime": runtime_env,
        "agent_framework": "Google ADK",
        "cloud_infrastructure": "Google Cloud Run" if runtime_env == "Google Cloud Run" else "local",
    }


@app.get("/version")
async def get_version() -> dict[str, Any]:
    return {
        "version": "0.4.1",
        "service": "astra-investigation-service",
        "runtime": detect_runtime(),
        "preregistration_sha256": "1b2eeaeb0a3f842cb4afaab755bd27fee469b818e05298bdbfd64d73ac0975a4",
        "agent_framework": "Google ADK",
        "gemini_model": os.getenv("ASTRA_GEMINI_MODEL", "gemini-3.5-flash-lite"),
    }


@app.get("/schema")
async def get_schema() -> dict[str, Any]:
    return InvestigationReport.model_json_schema()


@app.post("/agent/investigate")
async def agent_investigate(req: AgentInvestigateRequest) -> dict[str, Any]:
    """Execute end-to-end investigation orchestrated by Google ADK Agent."""
    start_time = time.perf_counter()
    data = generate_synthetic_market(points=req.points, seed=req.seed)
    
    agent = ASTRAInvestigationAgent(max_turns=req.max_turns)
    report = await agent.run_investigation(
        returns=data.returns,
        anomaly_idx=600,
        case_id=f"cloud-case-{req.scenario}-{req.seed}",
    )
    
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    # Emit structured Google Cloud log
    log_record = {
        "event": "astra_investigation_completed",
        "trace_id": report.trace_id,
        "case_id": report.case_id,
        "runtime": report.runtime,
        "agent_framework": report.agent_framework,
        "model": report.model,
        "executed_ops": report.executed_operations,
        "stop_reason": report.stop_reason.value,
        "decision": report.decision.value,
        "latency_ms": latency_ms,
    }
    logger.info(json.dumps(log_record))
    
    return report.model_dump()


@app.post("/investigate")
async def investigate(seed: int = 42, points: int = 2400, strategy: str = "evidence_driven") -> dict[str, Any]:
    settings = Settings(seed=seed, points=points)
    engine = InvestigationEngine(settings)
    report = await engine.investigate(strategy=strategy, force_reprocess=True)
    return report.model_dump()


@app.post("/judge-demo")
async def run_judge_demo() -> dict[str, Any]:
    settings = Settings(seed=42, points=2400)
    engine = InvestigationEngine(settings)
    report = await engine.investigate(strategy="evidence_driven", force_reprocess=True)
    return {
        "investigation_id": report.investigation_id,
        "run_id": report.run_id,
        "runtime": detect_runtime(),
        "agent_framework": "Google ADK",
        "initial_state": report.initial_state.value,
        "final_state": report.final_state.value,
        "decision": report.decision_outcome.decision.value if report.decision_outcome else "UNKNOWN",
        "primary_reason": report.decision_outcome.primary_reason if report.decision_outcome else "",
        "reason_codes": [r.value for r in report.decision_outcome.reason_codes] if report.decision_outcome else [],
        "tests_used": report.budget.tests_used,
        "cost_units": report.budget.cost_units_used,
        "total_latency_ms": report.metrics.get("total_latency_ms", 0),
        "competing_hypotheses": [
            {"id": h.id, "name": h.name, "score": h.evidence_score, "status": h.status.value}
            for h in report.competing_hypotheses
        ],
    }


@app.post("/real-demo")
async def run_real_demo() -> dict[str, Any]:
    adapter = RealMarketAdapter()
    data = adapter.load()
    engine = InvestigationEngine()
    report = await engine.investigate(data, strategy="evidence_driven", force_reprocess=True)
    return {
        "investigation_id": report.investigation_id,
        "track": report.execution_track,
        "dataset": adapter.name,
        "runtime": detect_runtime(),
        "decision": report.decision_outcome.decision.value if report.decision_outcome else "UNKNOWN",
        "primary_reason": report.decision_outcome.primary_reason if report.decision_outcome else "",
        "tests_used": report.budget.tests_used,
    }


@app.get("/telemetry/{run_id}")
async def get_telemetry(run_id: str) -> PlainTextResponse:
    path = Path("artifacts") / "runs" / f"{run_id}.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Telemetry run not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="application/x-jsonlines")
