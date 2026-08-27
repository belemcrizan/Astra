from __future__ import annotations

from typing import Any

from ..contracts import DSLOperation, DSLOperationName, InvestigationBudget, InvestigationHypothesis
from ..execution.dsl import DSL_OPERATION_SPECS, DSLOperationSpec


class DiscriminativeEvidenceSelector:
    """Selects investigation tests that maximize discrimination between competing hypotheses.
    
    Rather than generic data collection, tests are chosen based on expected information gain
    relative to resource cost.
    """

    @classmethod
    def select_best_test(
        cls,
        ranked_hypotheses: list[InvestigationHypothesis],
        budget: InvestigationBudget,
        executed_ops: set[DSLOperationName],
        anomaly_index: int | None = None,
    ) -> DSLOperation | None:
        if len(ranked_hypotheses) < 2:
            return None

        h_lead = ranked_hypotheses[0]
        h_second = ranked_hypotheses[1]
        target_pair = {h_lead.id, h_second.id}

        candidates: list[tuple[float, DSLOperation]] = []

        for op_name, spec in DSL_OPERATION_SPECS.items():
            if op_name in executed_ops:
                continue

            # Meta operations are not acquisition tests
            if op_name in (DSLOperationName.RECOMMEND_DECISION, DSLOperationName.EVALUATE_HYPOTHESIS):
                continue

            # Check budget feasibility
            if budget.cost_units_used + spec.cost_units > budget.max_cost_units:
                continue
            if budget.tests_used + 1 > budget.max_tests:
                continue

            # Calculate discrimination overlap
            overlap = len(target_pair.intersection(set(spec.discriminates)))
            if overlap == 0 and spec.discriminates:
                continue

            # Expected Information Gain heuristic
            score_diff = abs(h_lead.evidence_score - h_second.evidence_score)
            closeness_factor = 1.0 / (1.0 + score_diff)
            expected_info = (overlap / max(len(spec.discriminates), 1)) * closeness_factor
            
            if expected_info <= 0:
                continue

            # Efficiency = Info Value / Cost Units
            efficiency = expected_info / max(spec.cost_units, 0.5)

            # Build candidate operation with sensible default parameters
            args = {pname: pspec.default for pname, pspec in spec.params.items() if pspec.default is not None}
            if op_name == DSLOperationName.COMPARE_WINDOWS and anomaly_index is not None:
                args["center_idx"] = anomaly_index

            op = DSLOperation(
                op_name=op_name,
                args=args,
                target_hypotheses=list(target_pair),
                cost_units=spec.cost_units,
                expected_info_value=round(expected_info, 3),
                reasoning=f"Selected to discriminate {h_lead.id} ({h_lead.name}) vs {h_second.id} ({h_second.name}) with efficiency {efficiency:.2f}.",
            )
            candidates.append((efficiency, op))

        if not candidates:
            return None

        # Sort descending by efficiency
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
