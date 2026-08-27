from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np

from ..agents import CausalAgent, GovernanceAgent, GraphAgent, PhysicsAgent, RegimeAgent, SignalAgent, robust_zscore
from ..baselines import run_all_baselines
from ..config import Settings
from ..contracts import (
    AgentResult,
    AgentStatus,
    Decision,
    DecisionOutcome,
    DSLOperation,
    DSLOperationName,
    DSLResult,
    EvidenceItem,
    GovernanceResult,
    HypothesisStatus,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationReport,
    InvestigationState,
)
from ..datasets import SyntheticMarket, generate_synthetic_market
from ..evaluation import evaluate_detections
from ..execution.executor import DSLExecutor
from ..execution.validator import DSLValidator
from ..falsification.engine import FalsificationEngine
from ..hypotheses.pool import HypothesisPool
from ..observability import RunLogger
from ..planner.gemini_planner import InvestigationPlanner
from ..policy.decision import DecisionPolicy
from ..preregistration import PREREGISTRATION, preregistration_hash
from ..state.machine import InvestigationStateMachine

# In-memory idempotency cache for deduplication
_PROCESSED_EVENT_CACHE: set[str] = set()


class InvestigationEngine:
    """Bounded Autonomous Evidence-Driven Investigation Engine for ASTRA v0.3.
    
    Orchestrates the formal lifecycle:
    OBSERVING -> SIGNAL_DETECTED -> TRIAGING -> INVESTIGATING -> DECISION_READY -> CLOSED/WATCH/ESCALATE
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.planner = InvestigationPlanner(use_llm=getattr(self.settings, "use_llm", False))

    async def investigate(
        self,
        data: Any | None = None,
        strategy: str = "evidence_driven",
        budget: InvestigationBudget | None = None,
        force_reprocess: bool = False,
    ) -> InvestigationReport:
        started_perf = time.perf_counter()
        
        # 1. Dataset loading & provenance
        data = data or generate_synthetic_market(self.settings.points, self.settings.seed)
        dataset_sha256 = getattr(data, "sha256", "unknown")
        dataset_version = getattr(data, "version", "unknown")
        is_synthetic = getattr(data, "watermark", "") == "SYNTHETIC_ONLY_NOT_REAL_DATA"
        track_name = "Track A (Controlled Synthetic)" if is_synthetic else "Track B (Real Dataset)"

        # 2. Idempotency check
        event_fingerprint = f"{dataset_sha256}:{strategy}:{getattr(data, 'seed', 0)}"
        if event_fingerprint in _PROCESSED_EVENT_CACHE and not force_reprocess:
            # Emit telemetry about duplicate suppression
            pass
        _PROCESSED_EVENT_CACHE.add(event_fingerprint)

        # 3. Identifiers & Telemetry
        run_id = str(uuid4())
        correlation_id = str(uuid4())
        investigation_id = f"inv-{uuid4().hex[:8]}"
        logger = RunLogger(run_id, correlation_id, self.settings.output_dir)
        logger.emit(
            "investigation_started",
            investigation_id=investigation_id,
            dataset_version=dataset_version,
            dataset_sha256=dataset_sha256,
            track=track_name,
            strategy=strategy,
        )

        # 4. State Machine & Budget initialization
        sm = InvestigationStateMachine(initial_state=InvestigationState.OBSERVING, logger=logger)
        inv_budget = budget or InvestigationBudget()

        # 5. Signal Detection & Triage
        sm.transition_to(InvestigationState.SIGNAL_DETECTED, trigger="event_stream_anomaly_detected")
        
        # Fast preliminary scan
        z = robust_zscore(np.asarray(data.returns, dtype=float))
        anomalies = np.flatnonzero(np.abs(z) >= PREREGISTRATION["signal"]["robust_z_threshold"]).tolist()
        initial_anomaly_idx = anomalies[0] if anomalies else (len(data.returns) // 2)

        sm.transition_to(InvestigationState.TRIAGING, trigger="triage_scan_complete", metadata={"anomaly_count": len(anomalies)})

        # 6. Initialize Hypothesis Pool
        pool = HypothesisPool()
        sm.transition_to(InvestigationState.INVESTIGATING, trigger="competing_hypotheses_spawned")

        # 7. Execution Boundary setup
        executor = DSLExecutor(data)
        executed_ops: set[DSLOperationName] = set()
        dsl_plan: list[DSLOperation] = []
        dsl_results: list[DSLResult] = []
        evidence_log: list[EvidenceItem] = []

        # 8. Bounded Autonomous Investigation Loop
        while not sm.is_terminal and not inv_budget.is_exhausted():
            inv_budget.steps_used += 1

            # Propose operation
            proposed_op = self.planner.plan_next_step(
                current_state=sm.current_state,
                pool=pool,
                budget=inv_budget,
                executed_ops=executed_ops,
                anomaly_index=initial_anomaly_idx,
                strategy=strategy,
            )

            # Check if planner concluded with recommendation
            if proposed_op.op_name == DSLOperationName.RECOMMEND_DECISION:
                break

            # Validate proposed operation against sandbox & budget
            val_result = DSLValidator.validate(proposed_op, inv_budget)
            if not val_result.is_valid:
                logger.emit("dsl_validation_rejected", operation=proposed_op.op_name.value, error=val_result.error)
                dsl_results.append(DSLResult(
                    op_name=proposed_op.op_name,
                    status="rejected",
                    error=val_result.error,
                    cost_units=0.0,
                ))
                # Safe fallback: break to decision policy
                break

            sanitized_op = val_result.sanitized_operation
            dsl_plan.append(sanitized_op)
            executed_ops.add(sanitized_op.op_name)

            # Execute approved operation
            result = executor.execute(sanitized_op)
            dsl_results.append(result)

            # Update budget accounting
            inv_budget.tests_used += 1
            inv_budget.cost_units_used += result.cost_units
            inv_budget.runtime_ms_used += result.latency_ms

            # Log evidence items
            for ev_item in result.evidence_generated:
                evidence_log.append(ev_item)
                logger.emit(
                    "evidence_acquired",
                    evidence_id=ev_item.evidence_id,
                    code=ev_item.code,
                    value=ev_item.value,
                    passed=ev_item.passed,
                    cost_units=ev_item.cost_units,
                )

            # Falsification & Evidence Score Updating
            for sup_hid in result.supports:
                pool.update_evidence(
                    sup_hid,
                    delta=+0.12,
                    supporting_msg=f"Supported by test {result.op_name.value}",
                    test_name=result.op_name.value,
                )
            for cont_hid in result.contradicts:
                falsified, msg = FalsificationEngine.evaluate_result(cont_hid, result)
                pool.record_falsification_attempt(
                    cont_hid,
                    test_name=result.op_name.value,
                    falsified=falsified,
                    details={"observed": result.observed_value},
                )
                logger.emit(
                    "hypothesis_falsification_evaluated",
                    hypothesis_id=cont_hid,
                    test_name=result.op_name.value,
                    falsified=falsified,
                )

            # Check if decision threshold reached
            lead = pool.get_leading()
            if lead.evidence_score >= 0.70 or (lead.evidence_score >= 0.55 and len(pool.all()) > 1 and (lead.evidence_score - pool.all()[1].evidence_score) >= 0.30):
                if sm.can_transition_to(InvestigationState.DECISION_READY):
                    sm.transition_to(InvestigationState.DECISION_READY, trigger="conclusive_evidence_threshold_reached")
                    break

        # If loop exited due to budget
        if not sm.is_terminal and sm.current_state != InvestigationState.DECISION_READY:
            if sm.can_transition_to(InvestigationState.EVIDENCE_INSUFFICIENT):
                sm.transition_to(InvestigationState.EVIDENCE_INSUFFICIENT, trigger="budget_limit_reached")

        # 9. Final Decision Policy
        decision_outcome = DecisionPolicy.evaluate(pool, inv_budget, self.settings.min_evidence_score)

        # Transition state machine to final state
        target_state_map = {
            InvestigationDecision.CLOSE: InvestigationState.CLOSED,
            InvestigationDecision.WATCH: InvestigationState.WATCHING,
            InvestigationDecision.ESCALATE: InvestigationState.ESCALATED,
            InvestigationDecision.DEFER: InvestigationState.DEFERRED,
            InvestigationDecision.REQUEST_HUMAN_REVIEW: InvestigationState.HUMAN_REVIEW_REQUIRED,
        }
        final_target = target_state_map.get(decision_outcome.decision, InvestigationState.WATCHING)
        if sm.can_transition_to(final_target):
            sm.transition_to(final_target, trigger=f"policy_decision_{decision_outcome.decision.value}")

        # 10. Run parallel analytical agents for full scientific baseline comparison (preserving v0.2 metrics)
        analytical_agents = [SignalAgent(), RegimeAgent(), PhysicsAgent(), GraphAgent(), CausalAgent()]
        analytical_results = [agent.execute(data) for agent in analytical_agents]
        baselines = run_all_baselines(np.asarray(data.returns, dtype=float), PREREGISTRATION["baselines"])
        
        legacy_gov = GovernanceResult(
            decision=Decision.HUMAN_REVIEW if decision_outcome.human_review_required or decision_outcome.decision == InvestigationDecision.ESCALATE else (
                Decision.PASS if decision_outcome.decision == InvestigationDecision.CLOSE else Decision.INSUFFICIENT_EVIDENCE
            ),
            reason=decision_outcome.primary_reason,
            human_review_required=decision_outcome.human_review_required,
        )

        # 11. Scientific Evaluations (Strictly separate Track A from Track B)
        scientific_eval: dict[str, Any] = {}
        real_eval: dict[str, Any] | None = None
        tolerance = max(20, round(len(data.returns) * PREREGISTRATION["evaluation"]["change_tolerance_fraction"]))

        if is_synthetic:
            cp = next((r for r in analytical_results if r.agent_id == "regime-agent"), None)
            cp_points = cp.findings.get("change_points", []) if cp else []
            sig = next((r for r in analytical_results if r.agent_id == "signal-agent"), None)
            sig_anomalies = sig.findings.get("anomaly_indices", []) if sig else []
            
            true_regimes = getattr(data, "regime_changes", ())
            true_anomalies = getattr(data, "anomaly_times", ())
            regime_metrics = evaluate_detections(true_regimes, cp_points, tolerance, len(data.returns))
            anomaly_metrics = evaluate_detections(true_anomalies, sig_anomalies, PREREGISTRATION["evaluation"]["anomaly_tolerance_points"], len(data.returns))
            
            baseline_eval = {
                b.name: {
                    "change_points": b.change_points,
                    "parameters": b.parameters,
                    "metrics": evaluate_detections(true_regimes, b.change_points, tolerance, len(data.returns)).to_dict(),
                }
                for b in baselines
            }
            causal_res = next((r for r in analytical_results if r.agent_id == "causal-agent"), None)
            stacking = causal_res.findings.get("stacking", {}) if causal_res else {}

            scientific_eval = {
                "scope": "synthetic_controlled_benchmark_not_external_validation",
                "dataset": {
                    "watermark": getattr(data, "watermark", "SYNTHETIC"),
                    "sha256": dataset_sha256,
                    "points": len(data.returns),
                    "signal_amplitude": getattr(data, "signal_amplitude", 0.0),
                },
                "change_point_tolerance": tolerance,
                "true_regime_changes": list(true_regimes),
                "detected_regime_changes": cp_points,
                "regime_metrics": regime_metrics.to_dict(),
                "true_anomalies": list(true_anomalies),
                "detected_anomalies": sig_anomalies,
                "anomaly_metrics": anomaly_metrics.to_dict(),
                "stacking_h2": stacking,
                "baselines": baseline_eval,
            }
        else:
            real_eval = {
                "scope": "real_world_empirical_observation_no_ground_truth_assumed",
                "dataset": {
                    "version": dataset_version,
                    "watermark": getattr(data, "watermark", "REAL_DATA"),
                    "sha256": dataset_sha256,
                    "points": len(data.returns),
                },
                "detected_change_points_astra": [ev.value for ev in evidence_log if ev.code in ("CUSUM_DETECTIONS", "PELT_DETECTIONS", "BOCPD_DETECTIONS")],
                "evidence_summary": [ev.statement for ev in evidence_log],
                "ground_truth_status": "No synthetic labels manufactured for real-world telemetry.",
            }

        total_ms = (time.perf_counter() - started_perf) * 1000

        # 12. Reproducibility Manifest
        reproducibility = {
            "astra_version": "0.3.0",
            "methodology_version": PREREGISTRATION["methodology_version"],
            "preregistration_sha256": preregistration_hash(),
            "dataset_sha256": dataset_sha256,
            "seed": getattr(data, "seed", self.settings.seed),
            "points": len(data.returns),
            "execution_track": track_name,
            "llm_enabled": self.planner.use_llm,
            "model_identifier": self.planner.model if self.planner.use_llm else "deterministic-heuristic-sandbox",
        }

        # 13. Build InvestigationReport
        report = InvestigationReport(
            run_id=run_id,
            correlation_id=correlation_id,
            investigation_id=investigation_id,
            dataset_version=dataset_version,
            methodology_version=PREREGISTRATION["methodology_version"],
            preregistration_sha256=preregistration_hash(),
            seed=getattr(data, "seed", self.settings.seed),
            execution_track=track_name,
            initial_state=InvestigationState.OBSERVING,
            final_state=sm.current_state,
            state_history=sm.history,
            hypotheses=pool.to_legacy_hypotheses(),
            competing_hypotheses=pool.all(),
            evidence_log=evidence_log,
            dsl_plan=dsl_plan,
            dsl_results=dsl_results,
            budget=inv_budget,
            decision_outcome=decision_outcome,
            governance=legacy_gov,
            agents=analytical_results,
            metrics={
                "total_latency_ms": round(total_ms, 3),
                "tests_executed_count": len(dsl_results),
                "cost_units_used": round(inv_budget.cost_units_used, 2),
                "steps_taken": inv_budget.steps_used,
                "decision": decision_outcome.decision.value,
                "reason_codes": [r.value for r in decision_outcome.reason_codes],
                "human_review_required": decision_outcome.human_review_required,
                "agents_failed": sum(r.status == AgentStatus.FAILED for r in analytical_results),
            },
            scientific_evaluation=scientific_eval,
            real_world_evaluation=real_eval,
            reproducibility=reproducibility,
        )

        # 14. Save report artifacts
        report_dir = self.settings.output_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / f"{run_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        (report_dir / f"{run_id}.md").write_text(self._render_markdown(report), encoding="utf-8")

        logger.emit(
            "investigation_finished",
            decision=decision_outcome.decision.value,
            final_state=sm.current_state.value,
            total_latency_ms=round(total_ms, 3),
            cost_units_used=round(inv_budget.cost_units_used, 2),
        )

        return report

    def _render_markdown(self, report: InvestigationReport) -> str:
        dec = report.decision_outcome
        lines = [
            f"# ASTRA v0.3 Investigation Report — `{report.investigation_id}`",
            "",
            f"- **Execution Track:** `{report.execution_track}`",
            f"- **Run ID:** `{report.run_id}`",
            f"- **Correlation ID:** `{report.correlation_id}`",
            f"- **Dataset Version:** `{report.dataset_version}`",
            f"- **Methodology Version:** `{report.methodology_version}`",
            f"- **Preregistration SHA-256:** `{report.preregistration_sha256}`",
            f"- **Initial State:** `{report.initial_state.value}` $\\rightarrow$ **Final State:** `{report.final_state.value}`",
            f"- **Final Decision:** **`{dec.decision.value if dec else 'UNKNOWN'}`**",
            f"- **Reason Codes:** `{', '.join(r.value for r in dec.reason_codes)}`" if dec else "",
            f"- **Human Review Required:** `{'YES' if dec and dec.human_review_required else 'NO'}`",
            "",
            "## 1. Executive Summary",
            "",
            dec.primary_reason if dec else "Investigation concluded.",
            "",
            "## 2. Investigation State Machine Trajectory",
            "",
            "| Step | From State | To State | Trigger |",
            "|---|---|---|---|",
        ]
        for idx, rec in enumerate(report.state_history, 1):
            lines.append(f"| {idx} | `{rec.from_state.value}` | `{rec.to_state.value}` | `{rec.trigger}` |")

        lines += [
            "",
            "## 3. Competing Hypotheses & Falsification Outcomes",
            "",
        ]
        for h in report.competing_hypotheses:
            lines.append(f"### `{h.id}`: {h.name}")
            lines.append(f"- **Claim:** {h.claim}")
            lines.append(f"- **Evidence Score:** `{h.evidence_score:.0%}` (Status: **`{h.status.value.upper()}`**)")
            lines.append(f"- **Supporting Evidence:** {', '.join(h.supporting_evidence) if h.supporting_evidence else 'None'}")
            lines.append(f"- **Contradicting Evidence:** {', '.join(h.contradicting_evidence) if h.contradicting_evidence else 'None'}")
            lines.append(f"- **Falsification Attempts:** {h.falsification_attempts}")
            lines.append("")

        lines += [
            "## 4. Discriminative Tests & Restricted DSL Execution",
            "",
            "| Operation | Status | Cost | Latency | Discriminates | Supports | Contradicts |",
            "|---|---|---:|---:|---|---|---|",
        ]
        for res in report.dsl_results:
            lines.append(
                f"| `{res.op_name.value}` | `{res.status}` | {res.cost_units:.1f} | {res.latency_ms:.1f} ms | "
                f"`{', '.join(res.supports + res.contradicts)}` | `{', '.join(res.supports)}` | `{', '.join(res.contradicts)}` |"
            )

        lines += [
            "",
            "## 5. Acquired Evidence Items",
            "",
        ]
        for ev in report.evidence_log:
            lines.append(f"- **`{ev.code}`** (`{ev.evidence_id}`): {ev.statement} (Passed: `{ev.passed}` | Cost: `{ev.cost_units:.1f}`)")

        lines += [
            "",
            "## 6. Budget & Resource Usage",
            "",
            f"- **Steps Taken:** {report.budget.steps_used} / {report.budget.max_steps}",
            f"- **Tests Executed:** {report.budget.tests_used} / {report.budget.max_tests}",
            f"- **Cost Units Consumed:** {report.budget.cost_units_used:.2f} / {report.budget.max_cost_units:.2f}",
            f"- **Total Latency:** {report.metrics.get('total_latency_ms', 0):.2f} ms",
            "",
        ]

        if report.scientific_evaluation:
            lines += [
                "## 7. Track A: Controlled Synthetic Evaluation",
                "",
                "```json",
                json.dumps(report.scientific_evaluation, indent=2),
                "```",
                "",
            ]

        if report.real_world_evaluation:
            lines += [
                "## 7. Track B: Real-World Dataset Evaluation",
                "",
                "```json",
                json.dumps(report.real_world_evaluation, indent=2),
                "```",
                "",
            ]

        lines += [
            "## 8. Epistemic Limitations & Disclaimers",
            "",
        ]
        for lim in report.limitations:
            lines.append(f"- {lim}")
        lines.append("")

        return "\n".join(lines)
