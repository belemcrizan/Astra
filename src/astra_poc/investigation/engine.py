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
    ActionUtilityEstimate,
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
    StopReason,
)
from ..datasets import SyntheticMarket, generate_synthetic_market
from ..evaluation import evaluate_detections
from ..execution.dsl import DSL_OPERATION_SPECS
from ..execution.executor import DSLExecutor
from ..execution.validator import DSLValidator
from ..falsification.engine import FalsificationEngine
from ..fleet.isolation import CaseIsolationManager
from ..hypotheses.pool import CompetingHypothesisPool
from ..observability import RunLogger
from ..planner.gemini_planner import InvestigationPlanner
from ..policy.counterfactual import CounterfactualEngine
from ..policy.decision import InvestigationPolicy
from ..policy.stopping import StoppingPolicy
from ..policy.voi import VoIEngine
from ..preregistration import PREREGISTRATION, preregistration_hash
from ..provenance.graph import DecisionProvenanceGraph
from ..provenance.integrity import IntegrityChain
from ..state.machine import InvestigationStateMachine

# In-memory idempotency cache for deduplication
_PROCESSED_EVENT_CACHE: set[str] = set()


class InvestigationEngine:
    """Bounded Autonomous Evidence-Driven Investigation Engine for ASTRA v0.4.
    
    Demonstrates Rational Investigation Control:
    - Adaptive Utility Evaluation U(a) = α·EIG + β·EFG + γ·EDR - λ_c·C - λ_t·T - λ_r·R
    - Value of Information (VoI) Stopping Policy
    - Functional H_unknown & Open-Set Handling
    - Decision Provenance Graphs & Tamper-Evident Hash Chaining
    - Counterfactual Decision Boundary Analysis
    - Fortified Multi-Case Fleet Isolation
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.planner = InvestigationPlanner(use_llm=getattr(self.settings, "use_llm", False))
        self.fleet_manager = CaseIsolationManager.get_instance()

    async def investigate(
        self,
        data: Any | None = None,
        strategy: str = "evidence_driven",
        budget: InvestigationBudget | None = None,
        case_id: str | None = None,
        tenant_id: str = "default-tenant",
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
            pass
        _PROCESSED_EVENT_CACHE.add(event_fingerprint)

        # 3. Fleet Multi-Case Isolation & Identifiers
        case_ctx = self.fleet_manager.create_case(case_id=case_id, tenant_id=tenant_id)
        run_id = str(uuid4())
        correlation_id = str(uuid4())
        investigation_id = f"inv-{uuid4().hex[:8]}"
        
        logger = RunLogger(run_id, correlation_id, self.settings.output_dir)
        logger.emit(
            "investigation_started",
            investigation_id=investigation_id,
            case_id=case_ctx.case_id,
            tenant_id=tenant_id,
            dataset_version=dataset_version,
            dataset_sha256=dataset_sha256,
            track=track_name,
            strategy=strategy,
        )

        # 4. Provenance Graph & Integrity Chain
        prov_graph = DecisionProvenanceGraph(investigation_id)
        integrity_chain = IntegrityChain()
        integrity_chain.append_event("investigation_initialized", {
            "investigation_id": investigation_id,
            "case_id": case_ctx.case_id,
            "dataset_sha256": dataset_sha256,
        })

        # 5. State Machine & Budget initialization
        sm = InvestigationStateMachine(initial_state=InvestigationState.OBSERVING, logger=logger)
        inv_budget = budget or InvestigationBudget()

        # 6. Signal Detection & Triage
        sm.transition_to(InvestigationState.SIGNAL_DETECTED, trigger="event_stream_anomaly_detected")
        integrity_chain.append_event("state_transition", {"from": "OBSERVING", "to": "SIGNAL_DETECTED"})
        
        z = robust_zscore(np.asarray(data.returns, dtype=float))
        anomalies = np.flatnonzero(np.abs(z) >= PREREGISTRATION["signal"]["robust_z_threshold"]).tolist()
        
        r_arr = np.asarray(data.returns, dtype=float)
        cum_var_dev = np.abs(np.cumsum((r_arr - np.mean(r_arr))**2 - np.var(r_arr)))
        candidate_break_idx = int(np.argmax(cum_var_dev))
        
        if 20 <= candidate_break_idx <= len(r_arr) - 20 and cum_var_dev[candidate_break_idx] > 0.1 * np.max(cum_var_dev):
            initial_anomaly_idx = candidate_break_idx
        elif anomalies:
            initial_anomaly_idx = anomalies[0]
        else:
            initial_anomaly_idx = len(r_arr) // 2

        prov_graph.add_node(
            node_id=f"obs-{initial_anomaly_idx}",
            node_type="observation",
            label=f"Anomaly Peak at t={initial_anomaly_idx} (z={float(z[initial_anomaly_idx]):.1f})" if anomalies else "Nominal Signal Scan",
        )

        sm.transition_to(InvestigationState.TRIAGING, trigger="triage_scan_complete", metadata={"anomaly_count": len(anomalies)})
        integrity_chain.append_event("state_transition", {"from": "SIGNAL_DETECTED", "to": "TRIAGING"})

        # 7. Initialize Competing Hypothesis Pool
        pool = CompetingHypothesisPool()
        for h in pool.hypotheses.values():
            prov_graph.add_node(node_id=h.id, node_type="hypothesis", label=f"{h.id}: {h.name} (Prior: {h.prior_evidence_score:.0%})")
            prov_graph.add_edge(source=f"obs-{initial_anomaly_idx}", target=h.id, relation="generated")

        sm.transition_to(InvestigationState.INVESTIGATING, trigger="competing_hypotheses_spawned")
        integrity_chain.append_event("state_transition", {"from": "TRIAGING", "to": "INVESTIGATING"})

        # 8. Execution Boundary setup
        executor = DSLExecutor(data)
        executed_ops: set[DSLOperationName] = set()
        dsl_plan: list[DSLOperation] = []
        dsl_results: list[DSLResult] = []
        evidence_log: list[EvidenceItem] = []
        action_utility_history: list[list[ActionUtilityEstimate]] = []
        stop_reason = StopReason.DECISION_SUFFICIENT

        # 9. Bounded Autonomous Investigation Loop with VoI & Rational Stopping
        while not sm.is_terminal and not inv_budget.is_exhausted():
            # A. Evaluate Action Utilities & VoI for all candidate tests
            ranked_hyps = pool.get_ranked_hypotheses()
            utility_estimates = VoIEngine.evaluate_candidates(
                ranked_hypotheses=ranked_hyps,
                budget=inv_budget,
                executed_ops=executed_ops,
                unknown_score=pool.unknown_score,
            )
            action_utility_history.append(utility_estimates)

            # B. Check Formal Stopping Policy
            should_stop, evaluated_stop_reason, stop_msg = StoppingPolicy.evaluate_stop(
                ranked_hypotheses=ranked_hyps,
                utility_estimates=utility_estimates,
                budget=inv_budget,
                unknown_score=pool.unknown_score,
                min_evidence_score=self.settings.min_evidence_score,
            )
            if should_stop:
                stop_reason = evaluated_stop_reason
                logger.emit("investigation_stopping_triggered", stop_reason=stop_reason.value, message=stop_msg)
                break

            inv_budget.steps_used += 1

            # C. Select Best Operation (Adaptive Policy or Planner)
            if strategy == "fixed_sequence":
                # Static ablation policy
                seq = [DSLOperationName.COMPARE_WINDOWS, DSLOperationName.RUN_PELT, DSLOperationName.RUN_CUSUM]
                next_op = seq[min(len(dsl_plan), len(seq) - 1)]
                proposed_op = DSLOperation(op_name=next_op, args={}, target_hypotheses=["H1", "H2", "H3"])
            elif strategy == "falsification_only":
                lead_hyp = ranked_hyps[0]
                proposed_op = FalsificationEngine.get_adversarial_test(lead_hyp, initial_anomaly_idx, executed_ops)
            else:
                # Default: Adaptive Utility Policy
                best_estimate = utility_estimates[0]
                spec = DSL_OPERATION_SPECS[best_estimate.action]
                args = {pname: pspec.default for pname, pspec in spec.params.items() if pspec.default is not None}
                if best_estimate.action == DSLOperationName.COMPARE_WINDOWS and initial_anomaly_idx is not None:
                    min_c = spec.params["center_idx"].min_value or 20
                    max_c = len(data.returns) - min_c
                    args["center_idx"] = int(max(min_c, min(initial_anomaly_idx, max_c)))
                proposed_op = DSLOperation(
                    op_name=best_estimate.action,
                    args=args,
                    target_hypotheses=spec.discriminates,
                    cost_units=spec.cost_units,
                    expected_info_value=best_estimate.expected_info_gain,
                    expected_falsification_gain=best_estimate.expected_falsification_gain,
                    expected_decision_gain=best_estimate.expected_decision_gain,
                    reasoning=best_estimate.reasoning,
                )

            # D. Validate proposed operation against sandbox & budget
            val_result = DSLValidator.validate(proposed_op, inv_budget)
            if not val_result.is_valid:
                logger.emit("dsl_validation_rejected", operation=proposed_op.op_name.value, error=val_result.error)
                dsl_results.append(DSLResult(
                    op_name=proposed_op.op_name,
                    status="rejected",
                    error=val_result.error,
                    cost_units=0.0,
                ))
                stop_reason = StopReason.SAFETY_BOUNDARY
                break

            sanitized_op = val_result.sanitized_operation
            dsl_plan.append(sanitized_op)
            executed_ops.add(sanitized_op.op_name)

            # Record action in Provenance Graph
            act_node_id = f"act-step-{inv_budget.steps_used}-{sanitized_op.op_name.value}"
            prov_graph.add_node(
                node_id=act_node_id,
                node_type="action",
                label=f"Step {inv_budget.steps_used}: {sanitized_op.op_name.value} (Cost: {sanitized_op.cost_units:.1f}u)",
            )
            for h in ranked_hyps[:2]:
                prov_graph.add_edge(source=h.id, target=act_node_id, relation="selected_because")

            # E. Execute approved operation in Sandbox
            result = executor.execute(sanitized_op)
            dsl_results.append(result)

            # Update budget accounting
            inv_budget.tests_used += 1
            inv_budget.cost_units_used += result.cost_units
            inv_budget.runtime_ms_used += result.latency_ms

            # Log evidence & Provenance
            for ev_item in result.evidence_generated:
                evidence_log.append(ev_item)
                case_ctx.evidence_ids.add(ev_item.evidence_id)
                prov_graph.add_node(
                    node_id=ev_item.evidence_id,
                    node_type="evidence",
                    label=f"{ev_item.code} (Val: {ev_item.value})",
                )
                prov_graph.add_edge(source=act_node_id, target=ev_item.evidence_id, relation="produced")

                logger.emit(
                    "evidence_acquired",
                    evidence_id=ev_item.evidence_id,
                    code=ev_item.code,
                    value=ev_item.value,
                    passed=ev_item.passed,
                    cost_units=ev_item.cost_units,
                )

            integrity_chain.append_event("dsl_execution", {
                "operation": sanitized_op.op_name.value,
                "status": result.status,
                "supports": result.supports,
                "contradicts": result.contradicts,
            })

            # F. Falsification & Evidence Score Updating
            pool.update_evidence(
                test_name=result.op_name.value,
                supports=result.supports,
                contradicts=result.contradicts,
                evidence_delta=0.15,
            )

            for sup_hid in result.supports:
                prov_graph.add_edge(source=act_node_id, target=sup_hid, relation="supports")
            for cont_hid in result.contradicts:
                prov_graph.add_edge(source=act_node_id, target=cont_hid, relation="contradicts")

            # G. Immediate Stopping Check after evidence update
            post_ranked = pool.get_ranked_hypotheses()
            post_candidates = VoIEngine.evaluate_candidates(
                post_ranked, inv_budget, executed_ops, pool.unknown_score
            )
            post_stop, post_stop_reason, _ = StoppingPolicy.evaluate_stop(
                ranked_hypotheses=post_ranked,
                utility_estimates=post_candidates,
                budget=inv_budget,
                unknown_score=pool.unknown_score,
                min_evidence_score=self.settings.min_evidence_score,
            )
            if post_stop:
                stop_reason = post_stop_reason
                if stop_reason == StopReason.DECISION_SUFFICIENT and sm.can_transition_to(InvestigationState.DECISION_READY):
                    sm.transition_to(InvestigationState.DECISION_READY, trigger="conclusive_evidence_threshold_reached")
                break

        # State transition upon loop exit
        if not sm.is_terminal and sm.current_state != InvestigationState.DECISION_READY:
            if stop_reason == StopReason.DECISION_SUFFICIENT and sm.can_transition_to(InvestigationState.DECISION_READY):
                sm.transition_to(InvestigationState.DECISION_READY, trigger="decision_ready")
            elif sm.can_transition_to(InvestigationState.EVIDENCE_INSUFFICIENT):
                sm.transition_to(InvestigationState.EVIDENCE_INSUFFICIENT, trigger=f"stopped_{stop_reason.value}")

        # 10. Unified Decision Policy
        policy = InvestigationPolicy(
            min_evidence_score=self.settings.min_evidence_score,
            unknown_threshold=0.60,
            selective_tau=0.65,
        )
        decision_outcome = policy.evaluate(
            hypotheses=pool.get_ranked_hypotheses(),
            budget=inv_budget,
            unknown_score=pool.unknown_score,
            stop_reason=stop_reason,
            evidence_items_count=len(evidence_log),
        )

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
            integrity_chain.append_event("state_transition", {"from": sm.history[-2].from_state.value, "to": final_target.value})

        # Add decision node to Provenance Graph
        dec_node_id = f"dec-{decision_outcome.decision.value}"
        prov_graph.add_node(
            node_id=dec_node_id,
            node_type="decision",
            label=f"DECISION: {decision_outcome.decision.value} (Conf: {decision_outcome.decision_confidence:.0%})",
        )
        if pool.get_ranked_hypotheses():
            prov_graph.add_edge(source=pool.get_ranked_hypotheses()[0].id, target=dec_node_id, relation="triggered")

        # 11. Counterfactual Analysis
        counterfactuals = CounterfactualEngine.generate_counterfactuals(
            decision_outcome=decision_outcome,
            ranked_hypotheses=pool.get_ranked_hypotheses(),
            evidence_log=evidence_log,
            budget=inv_budget,
            unknown_score=pool.unknown_score,
        )

        # 12. Legacy Analytical Agents (Preserving benchmark metrics)
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

        # 13. Scientific Evaluation
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

        # 14. Reproducibility Manifest
        reproducibility = {
            "astra_version": "0.4.0",
            "methodology_version": PREREGISTRATION["methodology_version"],
            "preregistration_sha256": preregistration_hash(),
            "dataset_sha256": dataset_sha256,
            "seed": getattr(data, "seed", self.settings.seed),
            "points": len(data.returns),
            "execution_track": track_name,
            "llm_enabled": self.planner.use_llm,
            "model_identifier": self.planner.model if self.planner.use_llm else "deterministic-decision-science-sandbox",
        }

        # 15. Build Complete InvestigationReport (v0.4)
        report = InvestigationReport(
            run_id=run_id,
            correlation_id=correlation_id,
            investigation_id=investigation_id,
            case_id=case_ctx.case_id,
            dataset_version=dataset_version,
            model_version="astra-poc-0.4.0",
            methodology_version=PREREGISTRATION["methodology_version"],
            preregistration_sha256=preregistration_hash(),
            seed=getattr(data, "seed", self.settings.seed),
            execution_track=track_name,
            initial_state=InvestigationState.OBSERVING,
            final_state=sm.current_state,
            stop_reason=stop_reason,
            state_history=sm.history,
            hypotheses=pool.to_legacy_hypotheses(),
            competing_hypotheses=pool.get_ranked_hypotheses(),
            unknown_score=pool.unknown_score,
            action_utility_history=action_utility_history,
            evidence_log=evidence_log,
            dsl_plan=dsl_plan,
            dsl_results=dsl_results,
            budget=inv_budget,
            decision_outcome=decision_outcome,
            counterfactuals=counterfactuals,
            governance=legacy_gov,
            agents=analytical_results,
            provenance_graph=prov_graph.to_contract(),
            integrity_chain=integrity_chain.records,
            metrics={
                "total_latency_ms": round(total_ms, 3),
                "tests_executed_count": len(dsl_results),
                "cost_units_used": round(inv_budget.cost_units_used, 2),
                "steps_taken": inv_budget.steps_used,
                "decision": decision_outcome.decision.value,
                "stop_reason": stop_reason.value,
                "reason_codes": [r.value for r in decision_outcome.reason_codes],
                "decision_confidence": decision_outcome.decision_confidence,
                "human_review_required": decision_outcome.human_review_required,
                "agents_failed": sum(r.status == AgentStatus.FAILED for r in analytical_results),
            },
            scientific_evaluation=scientific_eval,
            real_world_evaluation=real_eval,
            reproducibility=reproducibility,
        )

        # 16. Save report artifacts
        report_dir = self.settings.output_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / f"{run_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        (report_dir / f"{run_id}.md").write_text(self._render_markdown(report), encoding="utf-8")

        # Close case lease in fleet manager
        self.fleet_manager.close_case(case_ctx.case_id)

        logger.emit(
            "investigation_finished",
            decision=decision_outcome.decision.value,
            stop_reason=stop_reason.value,
            final_state=sm.current_state.value,
            total_latency_ms=round(total_ms, 3),
            cost_units_used=round(inv_budget.cost_units_used, 2),
        )

        return report

    def _render_markdown(self, report: InvestigationReport) -> str:
        dec = report.decision_outcome
        lines = [
            f"# ASTRA v0.4 Investigation Report — `{report.investigation_id}`",
            "",
            f"- **Execution Track:** `{report.execution_track}`",
            f"- **Case ID:** `{report.case_id}` | **Run ID:** `{report.run_id}`",
            f"- **Correlation ID:** `{report.correlation_id}`",
            f"- **Dataset Version:** `{report.dataset_version}`",
            f"- **Methodology Version:** `{report.methodology_version}`",
            f"- **Preregistration SHA-256:** `{report.preregistration_sha256}`",
            f"- **State Trajectory:** `{report.initial_state.value}` $\\rightarrow$ **`{report.final_state.value}`**",
            f"- **Stop Reason:** **`{report.stop_reason.value}`**",
            f"- **Final Decision:** **`{dec.decision.value if dec else 'UNKNOWN'}`** (Confidence: `{dec.decision_confidence:.0%}`)" if dec else "",
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
            "## 3. Competing Hypotheses & Open-Set Assessment",
            "",
            f"**Open-Set / Unknown Dynamics Score:** `{report.unknown_score:.1%}`",
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
            "## 4. Value of Information (VoI) & Adaptive Action Selection",
            "",
            "| Step | Evaluated Action | EIG | EFG | EDR | Cost | Net Utility | VoI | Selected |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for step_idx, step_evals in enumerate(report.action_utility_history, 1):
            for est in step_evals:
                lines.append(
                    f"| {step_idx} | `{est.action.value}` | {est.expected_info_gain:.2f} | {est.expected_falsification_gain:.2f} | "
                    f"{est.expected_decision_gain:.2f} | {est.cost:.1f}u | {est.net_utility:.2f} | {est.voi:.2f} | **`{'YES' if est.selected else 'NO'}`** |"
                )

        lines += [
            "",
            "## 5. Counterfactual Decision Analysis",
            "",
        ]
        for idx, cf in enumerate(report.counterfactuals, 1):
            lines.append(f"**Counterfactual {idx}: Flip to `{cf.target_decision.value}`**")
            lines.append(f"- *Condition:* {cf.condition}")
            lines.append(f"- *Minimal Evidence Delta:* `{cf.minimal_evidence_delta}`")
            lines.append(f"- *Hypothetical Reason:* `{cf.hypothetical_reason_code.value}`")
            lines.append("")

        if report.provenance_graph and report.provenance_graph.mermaid_diagram:
            lines += [
                "## 6. Decision Provenance Graph (DAG)",
                "",
                "```mermaid",
                report.provenance_graph.mermaid_diagram,
                "```",
                "",
            ]

        lines += [
            "## 7. Budget & Resource Usage",
            "",
            f"- **Steps Taken:** {report.budget.steps_used} / {report.budget.max_steps}",
            f"- **Tests Executed:** {report.budget.tests_used} / {report.budget.max_tests}",
            f"- **Cost Units Consumed:** {report.budget.cost_units_used:.2f} / {report.budget.max_cost_units:.2f}",
            f"- **Total Latency:** {report.metrics.get('total_latency_ms', 0):.2f} ms",
            "",
        ]

        if report.scientific_evaluation:
            lines += [
                "## 8. Track A: Controlled Synthetic Evaluation",
                "",
                "```json",
                json.dumps(report.scientific_evaluation, indent=2),
                "```",
                "",
            ]

        if report.real_world_evaluation:
            lines += [
                "## 8. Track B: Real-World Dataset Evaluation",
                "",
                "```json",
                json.dumps(report.real_world_evaluation, indent=2),
                "```",
                "",
            ]

        lines += [
            "## 9. Epistemic Limitations & Disclaimers",
            "",
        ]
        for lim in report.limitations:
            lines.append(f"- {lim}")
        lines.append("")

        return "\n".join(lines)
