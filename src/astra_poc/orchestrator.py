from __future__ import annotations

import asyncio
from typing import Any

from .config import Settings
from .contracts import InvestigationReport
from .datasets import SyntheticMarket, generate_synthetic_market
from .investigation.engine import InvestigationEngine


class CircuitBreaker:
    def __init__(self, failure_limit: int = 2):
        self.failure_limit = failure_limit
        self.failures: dict[str, int] = {}

    def allow(self, agent_id: str) -> bool:
        return self.failures.get(agent_id, 0) < self.failure_limit

    def record(self, agent_id: str, failed: bool) -> None:
        if failed:
            self.failures[agent_id] = self.failures.get(agent_id, 0) + 1


class OrchestratorAgent:
    """Orchestrator Agent entry point (retained for backward compatibility and lifecycle control)."""

    agent_id = "orchestrator-agent"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = InvestigationEngine(settings)

    async def investigate(self, data: SyntheticMarket | None = None) -> InvestigationReport:
        return await self.engine.investigate(data=data, force_reprocess=True)
