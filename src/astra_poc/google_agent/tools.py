from __future__ import annotations

from typing import Any

from ..contracts import (
    DSLOperation,
    DSLOperationName,
    DSLResult,
    InvestigationBudget,
    InvestigationHypothesis,
)
from ..execution.dsl import DSL_OPERATION_SPECS
from ..execution.executor import DSLExecutor
from ..execution.validator import DSLValidator
from ..hypotheses.pool import CompetingHypothesisPool
from ..state.machine import InvestigationState, InvestigationStateMachine


class ASTRAInvestigationTools:
    """Bounded, security-hardened toolset exposed to Google ADK Agent."""

    def __init__(
        self,
        pool: CompetingHypothesisPool,
        budget: InvestigationBudget,
        executor: DSLExecutor,
        state_machine: InvestigationStateMachine,
        anomaly_idx: int = 600,
    ) -> None:
        self.pool = pool
        self.budget = budget
        self.executor = executor
        self.state_machine = state_machine
        self.anomaly_idx = anomaly_idx
        self.executed_ops: set[DSLOperationName] = set()
        self.results_history: list[DSLResult] = []

    def get_investigation_state(self) -> dict[str, Any]:
        """Returns the current state machine phase and remaining computational budget."""
        return {
            "current_state": self.state_machine.current_state.value,
            "is_terminal": self.state_machine.is_terminal,
            "steps_used": self.budget.steps_used,
            "max_steps": self.budget.max_steps,
            "tests_used": self.budget.tests_used,
            "max_tests": self.budget.max_tests,
            "cost_units_used": round(self.budget.cost_units_used, 2),
            "max_cost_units": self.budget.max_cost_units,
            "budget_exhausted": self.budget.is_exhausted(),
            "anomaly_index": self.anomaly_idx,
        }

    def get_competing_hypotheses(self) -> list[dict[str, Any]]:
        """Returns the ranked pool of competing hypotheses with current evidence scores."""
        ranked = self.pool.get_ranked_hypotheses()
        return [
            {
                "id": h.id,
                "name": h.name,
                "claim": h.claim,
                "evidence_score": round(h.evidence_score, 3),
                "status": h.status.value,
                "falsification_attempts": h.falsification_attempts,
                "supporting_evidence": h.supporting_evidence,
                "contradicting_evidence": h.contradicting_evidence,
            }
            for h in ranked
        ]

    def get_available_experiments(self) -> list[dict[str, Any]]:
        """Returns all allowed Restricted DSL operations that have not yet been executed."""
        available = []
        for op_name, spec in DSL_OPERATION_SPECS.items():
            if op_name in self.executed_ops:
                continue
            if op_name in (DSLOperationName.RECOMMEND_DECISION, DSLOperationName.EVALUATE_HYPOTHESIS, DSLOperationName.ASK_HUMAN):
                continue
            available.append({
                "operation": op_name.value,
                "cost_units": spec.cost_units,
                "discriminates": spec.discriminates,
                "description": spec.description,
                "parameters": {
                    k: {"type": v.type_name, "default": v.default, "min": v.min_value, "max": v.max_value}
                    for k, v in spec.params.items()
                },
            })
        return available

    def execute_bounded_experiment(self, op_name_str: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validates and executes a proposed DSL operation in ASTRA's deterministic sandbox."""
        try:
            op_enum = DSLOperationName(op_name_str)
        except ValueError:
            return {
                "status": "rejected",
                "error": f"Operation '{op_name_str}' is not in ASTRA Restricted DSL catalog.",
                "validation_passed": False,
            }

        args = args or {}
        spec = DSL_OPERATION_SPECS.get(op_enum)
        if not spec:
            return {"status": "rejected", "error": "Spec not found", "validation_passed": False}

        # Fill defaults
        for pname, pspec in spec.params.items():
            if pname not in args and pspec.default is not None:
                args[pname] = pspec.default

        if op_enum == DSLOperationName.COMPARE_WINDOWS and "center_idx" in spec.params:
            if "center_idx" not in args or args["center_idx"] is None:
                min_c = spec.params["center_idx"].min_value or 20
                args["center_idx"] = max(min_c, min(self.anomaly_idx, len(self.executor.returns) - min_c))

        proposed_op = DSLOperation(
            op_name=op_enum,
            args=args,
            target_hypotheses=spec.discriminates,
            cost_units=spec.cost_units,
        )

        # 1. Independent DSL Validation Boundary
        val_result = DSLValidator.validate(proposed_op, self.budget)
        if not val_result.is_valid:
            return {
                "status": "rejected",
                "error": val_result.error,
                "validation_passed": False,
                "operation": op_name_str,
            }

        sanitized_op = val_result.sanitized_operation
        self.executed_ops.add(sanitized_op.op_name)

        # 2. Deterministic Sandboxed Execution
        result = self.executor.execute(sanitized_op)
        self.results_history.append(result)

        # 3. Budget accounting
        self.budget.steps_used += 1
        self.budget.tests_used += 1
        self.budget.cost_units_used += result.cost_units
        self.budget.runtime_ms_used += result.latency_ms

        # 4. Hypothesis updating
        self.pool.update_evidence(
            test_name=result.op_name.value,
            supports=result.supports,
            contradicts=result.contradicts,
            evidence_delta=0.15,
        )

        return {
            "status": "success",
            "validation_passed": True,
            "operation": sanitized_op.op_name.value,
            "cost_units": result.cost_units,
            "latency_ms": result.latency_ms,
            "supports": result.supports,
            "contradicts": result.contradicts,
            "evidence": [e.statement for e in result.evidence_generated],
            "ranked_hypotheses": [
                {"id": h.id, "evidence_score": h.evidence_score, "status": h.status.value}
                for h in self.pool.get_ranked_hypotheses()
            ],
        }
