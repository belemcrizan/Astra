from __future__ import annotations

import unittest

from astra_poc.contracts import DSLOperationName, InvestigationBudget
from astra_poc.evidence.acquisition import DiscriminativeEvidenceSelector
from astra_poc.hypotheses.pool import HypothesisPool


class EvidenceAcquisitionTests(unittest.TestCase):
    def test_selector_chooses_discriminative_test_for_top_contenders(self):
        pool = HypothesisPool()
        budget = InvestigationBudget(max_cost_units=10.0)
        executed = set()

        op = DiscriminativeEvidenceSelector.select_best_test(
            ranked_hypotheses=pool.all(),
            budget=budget,
            executed_ops=executed,
            anomaly_index=720,
        )
        self.assertIsNotNone(op)
        self.assertIn(
            op.op_name,
            [
                DSLOperationName.RUN_CUSUM,
                DSLOperationName.RUN_PAGE_HINKLEY,
                DSLOperationName.RUN_PELT,
                DSLOperationName.COMPARE_WINDOWS,
                DSLOperationName.CALCULATE_ENTROPY,
                DSLOperationName.CHECK_SUSCEPTIBILITY,
            ],
        )

    def test_selector_respects_budget_constraints(self):
        pool = HypothesisPool()
        budget = InvestigationBudget(max_cost_units=1.0, cost_units_used=0.95)  # Only 0.05 remaining, lower than min test cost 0.2
        executed = set()

        op = DiscriminativeEvidenceSelector.select_best_test(
            ranked_hypotheses=pool.all(),
            budget=budget,
            executed_ops=executed,
        )
        self.assertIsNone(op)


if __name__ == "__main__":
    unittest.main()
