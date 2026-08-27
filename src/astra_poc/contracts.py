from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Legacy & Shared Enums (backward compatible)
# ---------------------------------------------------------------------------

class AgentStatus(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class Decision(StrEnum):
    PASS = "pass"
    HUMAN_REVIEW = "human_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BLOCKED = "blocked"


# ---------------------------------------------------------------------------
# Investigation State Machine Enums & Contracts (v0.3)
# ---------------------------------------------------------------------------

class InvestigationState(StrEnum):
    OBSERVING = "OBSERVING"
    SIGNAL_DETECTED = "SIGNAL_DETECTED"
    TRIAGING = "TRIAGING"
    INVESTIGATING = "INVESTIGATING"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    DECISION_READY = "DECISION_READY"
    CLOSED = "CLOSED"
    WATCHING = "WATCHING"
    ESCALATED = "ESCALATED"
    DEFERRED = "DEFERRED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class InvestigationDecision(StrEnum):
    CLOSE = "CLOSE"
    WATCH = "WATCH"
    ESCALATE = "ESCALATE"
    DEFER = "DEFER"
    REQUEST_HUMAN_REVIEW = "REQUEST_HUMAN_REVIEW"


class DecisionReasonCode(StrEnum):
    TRANSIENT_NOISE_CONFIRMED = "TRANSIENT_NOISE_CONFIRMED"
    REGIME_SHIFT_CONFIRMED = "REGIME_SHIFT_CONFIRMED"
    STRUCTURAL_BREAK_SUPPORTED = "STRUCTURAL_BREAK_SUPPORTED"
    COORDINATED_WEAK_SIGNAL_DETECTED = "COORDINATED_WEAK_SIGNAL_DETECTED"
    ALTERNATIVE_NOT_FALSIFIED = "ALTERNATIVE_NOT_FALSIFIED"
    MATERIAL_UNCERTAINTY = "MATERIAL_UNCERTAINTY"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    GOVERNANCE_POLICY_REQUIRED = "GOVERNANCE_POLICY_REQUIRED"
    BENIGN_FLUCTUATION_SURVIVED = "BENIGN_FLUCTUATION_SURVIVED"
    TEST_FAILURE_DEGRADATION = "TEST_FAILURE_DEGRADATION"
    UNAUTHORIZED_ACTION_BLOCKED = "UNAUTHORIZED_ACTION_BLOCKED"


class HypothesisStatus(StrEnum):
    ACTIVE = "active"
    LEADING = "leading"
    CHALLENGED = "challenged"
    FALSIFIED = "falsified"
    CONFIRMED = "confirmed"
    INCONCLUSIVE = "inconclusive"


class DSLOperationName(StrEnum):
    RUN_CUSUM = "RUN_CUSUM"
    RUN_PAGE_HINKLEY = "RUN_PAGE_HINKLEY"
    RUN_PELT = "RUN_PELT"
    RUN_BOCPD = "RUN_BOCPD"
    COMPARE_WINDOWS = "COMPARE_WINDOWS"
    CALCULATE_ENTROPY = "CALCULATE_ENTROPY"
    CHECK_SUSCEPTIBILITY = "CHECK_SUSCEPTIBILITY"
    TEST_TEMPORAL_STACKING = "TEST_TEMPORAL_STACKING"
    REQUEST_FEATURE = "REQUEST_FEATURE"
    EVALUATE_HYPOTHESIS = "EVALUATE_HYPOTHESIS"
    RECOMMEND_DECISION = "RECOMMEND_DECISION"


# ---------------------------------------------------------------------------
# Core Atomic Structures
# ---------------------------------------------------------------------------

class Evidence(BaseModel):
    code: str
    statement: str
    value: float | int | str | bool | None = None
    threshold: float | int | str | None = None
    passed: bool | None = None


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"ev-{uuid4().hex[:8]}")
    code: str
    statement: str
    value: float | int | str | bool | None = None
    threshold: float | int | str | None = None
    passed: bool | None = None
    hypotheses_discriminated: list[str] = Field(default_factory=list)
    why_selected: str | None = None
    expected_information_value: float = Field(default=0.5, ge=0.0, le=1.0)
    cost_units: float = Field(default=1.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    supporting_agents: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    falsification_status: str = "pending"
    counterevidence: list[str] = Field(default_factory=list)


class InvestigationHypothesis(BaseModel):
    id: str
    name: str
    claim: str
    prior_evidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Uncalibrated heuristic evidence score (not a probability).")
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    falsification_attempts: int = 0
    falsification_outcomes: list[dict[str, Any]] = Field(default_factory=list)
    tests_executed: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# DSL & Execution Models
# ---------------------------------------------------------------------------

class DSLOperation(BaseModel):
    op_name: DSLOperationName
    args: dict[str, Any] = Field(default_factory=dict)
    target_hypotheses: list[str] = Field(default_factory=list)
    cost_units: float = Field(default=1.0, ge=0.0)
    expected_info_value: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = ""


class DSLResult(BaseModel):
    op_name: DSLOperationName
    status: str = "success"  # success, rejected, failed, timeout
    observed_value: Any = None
    evidence_generated: list[EvidenceItem] = Field(default_factory=list)
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)
    cost_units: float = 1.0
    latency_ms: float = 0.0
    error: str | None = None


class InvestigationBudget(BaseModel):
    max_steps: int = Field(default=5, ge=1, le=20)
    max_tests: int = Field(default=6, ge=1, le=30)
    max_cost_units: float = Field(default=10.0, ge=1.0)
    max_runtime_ms: float = Field(default=5000.0, ge=100.0)
    steps_used: int = 0
    tests_used: int = 0
    cost_units_used: float = 0.0
    runtime_ms_used: float = 0.0

    def is_exhausted(self) -> bool:
        return (
            self.steps_used >= self.max_steps
            or self.tests_used >= self.max_tests
            or self.cost_units_used >= self.max_cost_units
            or self.runtime_ms_used >= self.max_runtime_ms
        )


class StateTransitionRecord(BaseModel):
    from_state: InvestigationState
    to_state: InvestigationState
    trigger: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Decision & Governance Models
# ---------------------------------------------------------------------------

class GovernanceResult(BaseModel):
    decision: Decision
    reason: str
    human_review_required: bool = True
    prohibited_actions: list[str] = Field(default_factory=lambda: [
        "execute financial orders",
        "block customers",
        "allege illicit conduct",
        "send external communications",
    ])


class DecisionOutcome(BaseModel):
    decision: InvestigationDecision
    reason_codes: list[DecisionReasonCode] = Field(default_factory=list)
    primary_reason: str
    human_review_required: bool = False
    prohibited_actions: list[str] = Field(default_factory=lambda: [
        "execute financial orders",
        "block customers",
        "allege illicit conduct",
        "send external communications",
    ])
    accepted_hypothesis_id: str | None = None
    residual_uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Observability / Telemetry Models
# ---------------------------------------------------------------------------

class TelemetrySpan(BaseModel):
    trace_id: str
    investigation_id: str
    event_id: str
    timestamp: str
    state: str
    component: str
    action: str
    hypothesis_id: str | None = None
    evidence_id: str | None = None
    decision: str | None = None
    reason_code: str | None = None
    latency_ms: float = 0.0
    cost_units: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Complete Investigation Report (v0.3)
# ---------------------------------------------------------------------------

class InvestigationReport(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    investigation_id: str = Field(default_factory=lambda: f"inv-{uuid4().hex[:8]}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_version: str
    model_version: str = "astra-poc-0.3.0"
    methodology_version: str
    preregistration_sha256: str
    seed: int
    execution_track: str = "Track A (Controlled Synthetic)"  # or "Track B (Real Dataset)"
    
    # State & Hypotheses
    initial_state: InvestigationState = InvestigationState.OBSERVING
    final_state: InvestigationState = InvestigationState.CLOSED
    state_history: list[StateTransitionRecord] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    competing_hypotheses: list[InvestigationHypothesis] = Field(default_factory=list)
    
    # Evidence & Execution
    evidence_log: list[EvidenceItem] = Field(default_factory=list)
    dsl_plan: list[DSLOperation] = Field(default_factory=list)
    dsl_results: list[DSLResult] = Field(default_factory=list)
    budget: InvestigationBudget = Field(default_factory=InvestigationBudget)
    
    # Decisions & Governance
    decision_outcome: DecisionOutcome | None = None
    governance: GovernanceResult
    agents: list[AgentResult] = Field(default_factory=list)
    
    # Metrics & Scientific Evaluations
    metrics: dict[str, Any] = Field(default_factory=dict)
    scientific_evaluation: dict[str, Any] = Field(default_factory=dict)
    real_world_evaluation: dict[str, Any] | None = None
    
    # Reproducibility Manifest
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=lambda: [
        "Synthetic performance does not establish external real-world validity.",
        "Evidence score is an uncalibrated heuristic ranking, not a calibrated probability.",
        "ASTRA is a proof of concept; no automated external intervention is permitted.",
        "Wilson confidence intervals reflect finite sample bounds within the tested model.",
        "Temporal null stacking supports association testing under circular shift, not causal identification.",
    ])
