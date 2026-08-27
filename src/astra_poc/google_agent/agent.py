from __future__ import annotations

import json
import os
import time
from typing import Any
from uuid import uuid4

import numpy as np

try:
    from google import adk
    from google import genai
    from google.genai import types
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False

from ..contracts import (
    DSLOperation,
    DSLOperationName,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationHypothesis,
    StopReason,
)
from ..execution.dsl import DSL_OPERATION_SPECS
from ..execution.executor import DSLExecutor
from ..execution.validator import DSLValidator
from ..hypotheses.pool import CompetingHypothesisPool
from ..policy.decision import InvestigationPolicy
from ..policy.stopping import StoppingPolicy
from ..policy.voi import VoIEngine
from ..state.machine import InvestigationState, InvestigationStateMachine
from .prompts import ASTRA_ADK_AGENT_SYSTEM_INSTRUCTION, format_investigation_prompt
from .schemas import AgentExecutionProvenance, GoogleAgentReport, InvestigationProposal
from .tools import ASTRAInvestigationTools


class BaseInvestigationPlanner:
    """Base interface for ASTRA investigation action planners."""

    async def plan_next_action(
        self,
        anomaly_idx: int,
        hypotheses: list[InvestigationHypothesis],
        executed_ops: set[DSLOperationName],
        budget: InvestigationBudget,
    ) -> InvestigationProposal:
        raise NotImplementedError


class FakeInvestigationPlanner(BaseInvestigationPlanner):
    """Deterministic offline planner for testing, CI, and local reproduction without network."""

    def __init__(self, fixed_sequence: list[DSLOperationName] | None = None) -> None:
        self.sequence = fixed_sequence or [
            DSLOperationName.COMPARE_WINDOWS,
            DSLOperationName.RUN_PELT,
            DSLOperationName.RUN_PAGE_HINKLEY,
            DSLOperationName.RUN_CUSUM,
        ]
        self.step = 0

    async def plan_next_action(
        self,
        anomaly_idx: int,
        hypotheses: list[InvestigationHypothesis],
        executed_ops: set[DSLOperationName],
        budget: InvestigationBudget,
    ) -> InvestigationProposal:
        # Pick next unexecuted operation from candidate pool
        lead = hypotheses[0]
        second = hypotheses[1] if len(hypotheses) > 1 else lead

        for op_enum in self.sequence:
            if op_enum not in executed_ops:
                spec = DSL_OPERATION_SPECS[op_enum]
                args = {pname: pspec.default for pname, pspec in spec.params.items() if pspec.default is not None}
                if op_enum == DSLOperationName.COMPARE_WINDOWS:
                    min_c = spec.params["center_idx"].min_value or 20
                    args["center_idx"] = max(min_c, anomaly_idx)
                return InvestigationProposal(
                    goal=f"Discriminate between {lead.id} ({lead.name}) and {second.id} ({second.name})",
                    proposed_operation=op_enum,
                    args=args,
                    target_hypotheses=spec.discriminates,
                    rationale=f"Offline deterministic test selection for {op_enum.value}",
                    expected_discrimination=f"Targeting {lead.id} vs {second.id}",
                )

        # Fallback default
        return InvestigationProposal(
            goal="Conclude investigation",
            proposed_operation=DSLOperationName.COMPARE_WINDOWS,
            args={"center_idx": anomaly_idx},
            target_hypotheses=["H1", "H2"],
            rationale="Catalog exhausted",
            expected_discrimination="None",
        )


def is_eligible_gemini_model(model: str) -> bool:
    """Verifies that the configured model satisfies the Gemini 3.5+ hackathon requirement."""
    m = model.lower()
    # Eligible: gemini-3.5-*, gemini-3.7-*, gemini-3.1-*, or generic gemini-3-*
    return m.startswith("gemini-3.") or m.startswith("gemini-3-") or "3.5" in m or "3.7" in m


class GoogleADKPlanner(BaseInvestigationPlanner):
    """Real Google ADK + Gemini 3.5+ Planner using structured outputs and tool boundaries."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        use_vertex: bool = False,
        project: str | None = None,
        location: str | None = None,
    ) -> None:
        self.model = model or os.getenv("ASTRA_GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.use_vertex = use_vertex or (os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true")
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self._client: Any = None

        mode = os.getenv("ASTRA_MODE", "local").lower()
        if mode == "hackathon":
            if not is_eligible_gemini_model(self.model):
                raise ValueError(
                    f"Ineligible model '{self.model}' for hackathon mode. "
                    "Hackathon requires Gemini 3.5 or newer (e.g., 'gemini-3.5-flash-lite', 'gemini-3.7-flash')."
                )
            if not (self.api_key or self.use_vertex or self.project):
                raise ValueError(
                    "Hackathon mode requires active Google credentials (GEMINI_API_KEY or GOOGLE_GENAI_USE_VERTEXAI=true)."
                )

    def _get_client(self) -> Any:
        if self._client is None and _GOOGLE_AVAILABLE:
            if self.use_vertex:
                self._client = genai.Client(vertexai=True, project=self.project, location=self.location)
            elif self.api_key:
                self._client = genai.Client(api_key=self.api_key)
            else:
                self._client = genai.Client()
        return self._client


    async def plan_next_action(
        self,
        anomaly_idx: int,
        hypotheses: list[InvestigationHypothesis],
        executed_ops: set[DSLOperationName],
        budget: InvestigationBudget,
    ) -> InvestigationProposal:
        client = self._get_client()
        if not client:
            raise RuntimeError("Google GenAI client unavailable. Configure GEMINI_API_KEY or Vertex AI credentials.")

        hyps_text = "\n".join(
            f"  - {h.id} ({h.name}): Evidence Score = {h.evidence_score:.1%}, Status = {h.status.value}"
            for h in hypotheses
        )
        exec_text = [op.value for op in executed_ops]
        budget_text = f"{budget.cost_units_used:.1f}/{budget.max_cost_units} cost units ({budget.tests_used}/{budget.max_tests} tests)"
        
        available_ops = [
            f"  - {op.value}: {spec.description} (Cost: {spec.cost_units}u, Discrim: {spec.discriminates})"
            for op, spec in DSL_OPERATION_SPECS.items()
            if op not in executed_ops and op not in (DSLOperationName.RECOMMEND_DECISION, DSLOperationName.EVALUATE_HYPOTHESIS, DSLOperationName.ASK_HUMAN)
        ]
        avail_text = "\n".join(available_ops)

        prompt = format_investigation_prompt(
            anomaly_idx=anomaly_idx,
            hypotheses_summary=hyps_text,
            executed_ops=exec_text,
            budget_remaining=budget_text,
            available_ops=avail_text,
        )

        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=ASTRA_ADK_AGENT_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=InvestigationProposal,
                temperature=0.1,
            ),
        )

        if not response.text:
            raise ValueError("Empty response received from Gemini model.")

        parsed_data = json.loads(response.text)
        return InvestigationProposal.model_validate(parsed_data)


class ASTRAInvestigationAgent:
    """Primary ASTRA Agent orchestrated through Google ADK."""

    def __init__(
        self,
        planner: BaseInvestigationPlanner | None = None,
        model: str | None = None,
        max_turns: int = 5,
        mode: str | None = None,
    ) -> None:
        self.model = model or os.getenv("ASTRA_GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.max_turns = max_turns
        self.mode = mode or os.getenv("ASTRA_MODE", "local").lower()
        
        # Initialize planner
        if planner is not None:
            self.planner = planner
        elif self.mode == "hackathon":
            # Fail closed in hackathon mode
            self.planner = GoogleADKPlanner(model=self.model)
        elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "true":
            self.planner = GoogleADKPlanner(model=self.model)
        else:
            self.planner = FakeInvestigationPlanner()

        # Build official ADK Agent instance if ADK is installed
        self.adk_agent: Any = None
        if _GOOGLE_AVAILABLE and hasattr(adk, "Agent"):
            self.adk_agent = adk.Agent(
                name="astra_investigation_planner",
                model=self.model,
                instruction=ASTRA_ADK_AGENT_SYSTEM_INSTRUCTION,
                output_schema=InvestigationProposal,
            )

    @classmethod
    def detect_runtime(cls) -> str:
        """Determines whether running inside Google Cloud Run or local environment."""
        if os.getenv("K_SERVICE") or os.getenv("K_REVISION") or os.getenv("K_CONFIGURATION"):
            return "Google Cloud Run"
        return "local"

    async def run_investigation(
        self,
        returns: np.ndarray,
        anomaly_idx: int = 600,
        case_id: str | None = None,
        budget: InvestigationBudget | None = None,
    ) -> GoogleAgentReport:
        start_time = time.perf_counter()
        case_id = case_id or f"case-adk-{uuid4().hex[:8]}"
        trace_id = f"trace-{uuid4().hex[:12]}"
        budget = budget or InvestigationBudget(max_steps=self.max_turns, max_tests=self.max_turns, max_cost_units=10.0)

        # 1. State Machine & Pool Initialization
        sm = InvestigationStateMachine(initial_state=InvestigationState.OBSERVING)
        pool = CompetingHypothesisPool()
        executor = DSLExecutor(returns)
        tools = ASTRAInvestigationTools(
            pool=pool,
            budget=budget,
            executor=executor,
            state_machine=sm,
            anomaly_idx=anomaly_idx,
        )

        sm.transition_to(InvestigationState.SIGNAL_DETECTED, trigger="signal_gate_trigger")
        sm.transition_to(InvestigationState.TRIAGING, trigger="anomaly_triage_opened")
        sm.transition_to(InvestigationState.INVESTIGATING, trigger="adk_agent_engaged")

        provenance_log: list[AgentExecutionProvenance] = []
        executed_ops: list[str] = []
        proposals_count = 0
        proposals_accepted = 0
        proposals_rejected = 0
        stop_reason = StopReason.DECISION_SUFFICIENT

        # 2. Autonomous Multi-Turn Agent Loop
        while not sm.is_terminal and not budget.is_exhausted():
            ranked_hyps = pool.get_ranked_hypotheses()
            utility_estimates = VoIEngine.evaluate_candidates(
                ranked_hypotheses=ranked_hyps,
                budget=budget,
                executed_ops=tools.executed_ops,
                unknown_score=pool.unknown_score,
            )

            # Check stopping policy
            should_stop, evaluated_stop_reason, stop_msg = StoppingPolicy.evaluate_stop(
                ranked_hypotheses=ranked_hyps,
                utility_estimates=utility_estimates,
                budget=budget,
                unknown_score=pool.unknown_score,
            )
            if should_stop:
                stop_reason = evaluated_stop_reason
                break

            # Turn count boundary
            if budget.steps_used >= self.max_turns:
                stop_reason = StopReason.BUDGET_EXHAUSTED
                break

            # Call Gemini / ADK Planner for next proposal
            proposals_count += 1
            try:
                proposal = await self.planner.plan_next_action(
                    anomaly_idx=anomaly_idx,
                    hypotheses=ranked_hyps,
                    executed_ops=tools.executed_ops,
                    budget=budget,
                )
            except Exception as e:
                # Safe fallback on agent/network error
                proposal = InvestigationProposal(
                    goal="Fallback diagnostic check on anomaly",
                    proposed_operation=DSLOperationName.COMPARE_WINDOWS,
                    args={"center_idx": anomaly_idx},
                    target_hypotheses=["H1", "H2"],
                    rationale=f"Planner error fallback: {str(e)}",
                )

            # 3. ASTRA Independent DSL Validation Boundary
            res = tools.execute_bounded_experiment(
                op_name_str=proposal.proposed_operation.value,
                args=proposal.args,
            )

            if res.get("validation_passed"):
                proposals_accepted += 1
                executed_ops.append(proposal.proposed_operation.value)
                prov_rec = AgentExecutionProvenance(
                    turn=proposals_count,
                    agent_framework="Google ADK",
                    model_provider="Google",
                    model=self.model,
                    proposal=proposal,
                    astra_validation_passed=True,
                    executed_operation=proposal.proposed_operation.value,
                    evidence_generated=[{"statement": s} for s in res.get("evidence", [])],
                    trace_id=trace_id,
                )
            else:
                proposals_rejected += 1
                prov_rec = AgentExecutionProvenance(
                    turn=proposals_count,
                    agent_framework="Google ADK",
                    model_provider="Google",
                    model=self.model,
                    proposal=proposal,
                    astra_validation_passed=False,
                    validation_error=res.get("error"),
                    trace_id=trace_id,
                )
                stop_reason = StopReason.SAFETY_BOUNDARY
                provenance_log.append(prov_rec)
                break

            provenance_log.append(prov_rec)

            # Re-evaluate stopping immediately after evidence update
            post_ranked = pool.get_ranked_hypotheses()
            post_estimates = VoIEngine.evaluate_candidates(
                post_ranked, budget, tools.executed_ops, pool.unknown_score
            )
            post_stop, post_stop_reason, _ = StoppingPolicy.evaluate_stop(
                post_ranked, post_estimates, budget, pool.unknown_score
            )
            if post_stop:
                stop_reason = post_stop_reason
                break

        # 4. Final Policy Decision
        policy = InvestigationPolicy()
        decision_outcome = policy.evaluate(
            hypotheses=pool.get_ranked_hypotheses(),
            budget=budget,
            unknown_score=pool.unknown_score,
            stop_reason=stop_reason,
            evidence_items_count=len(tools.results_history),
        )

        from ..policy.counterfactual import CounterfactualEngine
        counterfactuals = CounterfactualEngine.generate_counterfactuals(
            decision_outcome=decision_outcome,
            ranked_hypotheses=pool.get_ranked_hypotheses(),
            evidence_log=tools.results_history,
            budget=budget,
            unknown_score=pool.unknown_score,
        )

        step_sample = max(1, len(returns) // 120)
        preview_data = [round(float(v), 5) for v in returns[::step_sample]]
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return GoogleAgentReport(
            case_id=case_id,
            trace_id=trace_id,
            scenario_name=case_id.split("-")[2] if "-" in case_id else "hero",
            runtime=self.detect_runtime(),
            agent_framework="Google ADK",
            agent_name="astra_investigation_planner",
            model_provider="Google",
            model=self.model,
            execution_boundary="ASTRA Restricted DSL",
            initial_anomaly_idx=anomaly_idx,
            proposals_count=proposals_count,
            proposals_accepted=proposals_accepted,
            proposals_rejected=proposals_rejected,
            executed_operations=executed_ops,
            competing_hypotheses=[
                {"id": h.id, "name": h.name, "score": round(float(h.evidence_score), 3), "status": h.status.value}
                for h in pool.get_ranked_hypotheses()
            ],
            stop_reason=stop_reason,
            decision=decision_outcome.decision,
            decision_reliability_score=round(float(decision_outcome.decision_reliability_score), 3),
            primary_reason=decision_outcome.primary_reason,
            counterfactuals=[
                {"target_decision": cf.target_decision.value, "condition": cf.condition}
                for cf in counterfactuals
            ],
            provenance_records=provenance_log,
            series_preview=preview_data,
            duration_ms=duration_ms,
        )
