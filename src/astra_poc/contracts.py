from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class Decision(StrEnum):
    PASS = "pass"
    HUMAN_REVIEW = "human_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BLOCKED = "blocked"


class Evidence(BaseModel):
    code: str
    statement: str
    value: float | int | str | bool | None = None
    threshold: float | int | str | None = None
    passed: bool | None = None


class AgentResult(BaseModel):
    agent_id: str
    status: AgentStatus = AgentStatus.COMPLETED
    summary: str
    evidence_score: float = Field(ge=0, le=1, description="Uncalibrated operational score; not a probability.")
    latency_ms: float = Field(ge=0)
    evidence: list[Evidence] = Field(default_factory=list)
    findings: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Hypothesis(BaseModel):
    hypothesis_id: str
    claim: str
    evidence_score: float = Field(ge=0, le=1, description="Uncalibrated evidence ranking score.")
    supporting_agents: list[str]
    required_evidence: list[str]
    falsification_status: str = "pending"
    counterevidence: list[str] = Field(default_factory=list)


class GovernanceResult(BaseModel):
    decision: Decision
    reason: str
    human_review_required: bool = True
    prohibited_actions: list[str] = Field(default_factory=lambda: [
        "executar ordens financeiras",
        "bloquear clientes",
        "acusar pratica ilicita",
        "enviar comunicacoes externas",
    ])


class InvestigationReport(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_version: str
    model_version: str = "astra-poc-0.2.0"
    methodology_version: str
    preregistration_sha256: str
    seed: int
    agents: list[AgentResult]
    hypotheses: list[Hypothesis]
    governance: GovernanceResult
    metrics: dict[str, float | int | str | bool]
    scientific_evaluation: dict[str, Any]
