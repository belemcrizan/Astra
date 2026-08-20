from __future__ import annotations

from fastapi import FastAPI

from .config import Settings
from .orchestrator import OrchestratorAgent

app = FastAPI(
    title="ASTRA POC",
    version="0.2.0",
    description="Teste de sanidade passivo com metricas completas, baselines fortes e falsificacao temporal.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "mode": "passive-synthetic"}


@app.post("/demo")
async def run_demo(seed: int = 42, points: int = 2400):
    settings = Settings(seed=seed, points=points)
    return await OrchestratorAgent(settings).investigate()
