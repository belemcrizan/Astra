from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from .adapters.real_market import RealMarketAdapter
from .config import Settings
from .contracts import InvestigationReport
from .datasets import generate_synthetic_market
from .investigation.engine import InvestigationEngine

app = FastAPI(
    title="ASTRA Investigation Service",
    version="0.3.0",
    description="Evidence-Driven Autonomous Investigation Engine for Weak Signals and Regime Changes (POC).",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "astra-investigation-service",
        "version": "0.3.0",
        "mode": "bounded-evidence-driven",
    }


@app.get("/schema")
async def get_schema() -> dict[str, Any]:
    return InvestigationReport.model_json_schema()


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
