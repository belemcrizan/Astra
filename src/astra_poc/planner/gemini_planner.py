from __future__ import annotations

import json
import os
from typing import Any

from ..contracts import (
    DSLOperation,
    DSLOperationName,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationHypothesis,
    InvestigationState,
)
from ..evidence.acquisition import DiscriminativeEvidenceSelector
from ..execution.dsl import DSL_OPERATION_SPECS
from ..falsification.engine import FalsificationEngine
from ..hypotheses.pool import HypothesisPool


class InvestigationPlanner:
    """Structured Investigation Planner with optional Google Gemini API support and deterministic fallback.
    
    The planner proposes operations strictly conforming to the ASTRA DSL schema.
    It never emits raw Python or executes code directly.
    """

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash", use_llm: bool = False):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.use_llm = use_llm and bool(self.api_key)

    def plan_next_step(
        self,
        current_state: InvestigationState,
        pool: HypothesisPool,
        budget: InvestigationBudget,
        executed_ops: set[DSLOperationName],
        anomaly_index: int | None = None,
        strategy: str = "evidence_driven",  # "evidence_driven", "falsification_only", "random", "fixed"
    ) -> DSLOperation:
        """Plans the next DSLOperation based on the chosen strategy and state."""
        
        # 1. Check if budget is exhausted or decision ready
        if budget.is_exhausted() or current_state == InvestigationState.DECISION_READY:
            lead = pool.get_leading()
            return DSLOperation(
                op_name=DSLOperationName.RECOMMEND_DECISION,
                args={"decision": "ESCALATE" if lead.evidence_score >= 0.60 else "WATCH", "reason_code": "BUDGET_TERMINATION"},
                cost_units=0.0,
                reasoning="Resource limit reached; concluding investigation.",
            )

        # 2. Strategy routing
        if strategy == "fixed":
            # Fixed baseline: always runs CUSUM, then Page-Hinkley, then PELT, then BOCPD
            sequence = [
                DSLOperationName.RUN_CUSUM,
                DSLOperationName.RUN_PAGE_HINKLEY,
                DSLOperationName.RUN_PELT,
                DSLOperationName.RUN_BOCPD,
                DSLOperationName.CALCULATE_ENTROPY,
            ]
            for op_name in sequence:
                if op_name not in executed_ops:
                    spec = DSL_OPERATION_SPECS[op_name]
                    args = {pname: pspec.default for pname, pspec in spec.params.items() if pspec.default is not None}
                    return DSLOperation(
                        op_name=op_name,
                        args=args,
                        target_hypotheses=spec.discriminates,
                        cost_units=spec.cost_units,
                        reasoning="Fixed-sequence baseline step.",
                    )
            # Conclude if sequence finished
            return DSLOperation(
                op_name=DSLOperationName.RECOMMEND_DECISION,
                args={"decision": "WATCH", "reason_code": "FIXED_SEQUENCE_COMPLETE"},
                cost_units=0.0,
            )

        elif strategy == "falsification_only":
            lead = pool.get_leading()
            return FalsificationEngine.get_adversarial_test(lead, anomaly_index, executed_ops)

        # 3. Evidence-driven strategy (Default ASTRA)
        lead = pool.get_leading()
        ranked = pool.all()

        # If leading hypothesis has not faced adversarial falsification yet, prioritize falsification
        if lead.falsification_attempts == 0 and len(executed_ops) < 2:
            adv_test = FalsificationEngine.get_adversarial_test(lead, anomaly_index, executed_ops)
            if adv_test.op_name not in executed_ops:
                return adv_test

        # Otherwise, select discriminative evidence between top 2 competitors
        disc_test = DiscriminativeEvidenceSelector.select_best_test(
            ranked, budget, executed_ops, anomaly_index
        )
        if disc_test is not None:
            return disc_test

        # Fallback to remaining un-executed falsification tests
        for h in ranked:
            adv_test = FalsificationEngine.get_adversarial_test(h, anomaly_index, executed_ops)
            if adv_test.op_name not in executed_ops:
                return adv_test

        # If all informative tests exhausted, recommend decision
        return DSLOperation(
            op_name=DSLOperationName.RECOMMEND_DECISION,
            args={"decision": "WATCH", "reason_code": "TESTS_EXHAUSTED"},
            cost_units=0.0,
            reasoning="All viable discriminative tests executed.",
        )
