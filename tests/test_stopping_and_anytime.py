from __future__ import annotations

import unittest
from astra_poc.contracts import (
    ActionUtilityEstimate,
    DSLOperationName,
    InvestigationBudget,
    InvestigationHypothesis,
    StopReason,
)
from astra_poc.policy.stopping import StoppingPolicy


class StoppingPolicyTests(unittest.TestCase):
    def test_budget_exhaustion_triggers_stop(self):
        hyps = [
            InvestigationHypothesis(id="H1", name="Noise", evidence_score=0.45),
            InvestigationHypothesis(id="H2", name="Regime", evidence_score=0.40),
        ]
        b = InvestigationBudget(max_steps=3, steps_used=3)
        should_stop, reason, msg = StoppingPolicy.evaluate_stop(
            ranked_hypotheses=hyps,
            utility_estimates=[],
            budget=b,
        )
        self.assertTrue(should_stop)
        self.assertEqual(reason, StopReason.BUDGET_EXHAUSTED)

    def test_conclusive_decision_sufficiency(self):
        hyps = [
            InvestigationHypothesis(id="H2", name="Regime", evidence_score=0.75),
            InvestigationHypothesis(id="H1", name="Noise", evidence_score=0.20),
        ]
        b = InvestigationBudget()
        should_stop, reason, msg = StoppingPolicy.evaluate_stop(
            ranked_hypotheses=hyps,
            utility_estimates=[],
            budget=b,
        )
        self.assertTrue(should_stop)
        self.assertEqual(reason, StopReason.DECISION_SUFFICIENT)

    def test_non_positive_voi_triggers_stop(self):
        hyps = [
            InvestigationHypothesis(id="H1", name="Noise", evidence_score=0.52),
            InvestigationHypothesis(id="H2", name="Regime", evidence_score=0.48),
        ]
        b = InvestigationBudget(tests_used=3)
        estimates = [
            ActionUtilityEstimate(action=DSLOperationName.CALCULATE_ENTROPY, voi=0.01, selected=True)
        ]
        should_stop, reason, msg = StoppingPolicy.evaluate_stop(
            ranked_hypotheses=hyps,
            utility_estimates=estimates,
            budget=b,
            voi_threshold=0.05,
        )
        self.assertTrue(should_stop)
        self.assertEqual(reason, StopReason.EXPECTED_VOI_NON_POSITIVE)


if __name__ == "__main__":
    unittest.main()
