from __future__ import annotations

import unittest
from astra_poc.contracts import DSLOperationName, InvestigationBudget, InvestigationHypothesis
from astra_poc.policy.voi import VoIEngine
from astra_poc.policy.recoverability import ActionRecoverabilityModel, DecisionCostModel
from astra_poc.contracts import InvestigationDecision


class PolicyAndVoITests(unittest.TestCase):
    def setUp(self):
        self.hyps = [
            InvestigationHypothesis(id="H1", name="Noise", evidence_score=0.55),
            InvestigationHypothesis(id="H2", name="Regime", evidence_score=0.45),
            InvestigationHypothesis(id="H3", name="Break", evidence_score=0.20),
            InvestigationHypothesis(id="H4", name="Signal", evidence_score=0.10),
            InvestigationHypothesis(id="H_unknown", name="Unknown", evidence_score=0.20),
        ]
        self.budget = InvestigationBudget(max_cost_units=10.0, cost_units_used=2.0)

    def test_voi_engine_ranks_candidate_actions(self):
        estimates = VoIEngine.evaluate_candidates(
            ranked_hypotheses=self.hyps,
            budget=self.budget,
            executed_ops=set(),
        )
        self.assertGreater(len(estimates), 0)
        top_action = estimates[0]
        self.assertTrue(top_action.selected)
        self.assertGreaterEqual(top_action.expected_info_gain, 0.0)
        self.assertGreaterEqual(top_action.expected_falsification_gain, 0.0)

    def test_executed_operations_are_filtered(self):
        executed = {DSLOperationName.COMPARE_WINDOWS, DSLOperationName.RUN_PELT}
        estimates = VoIEngine.evaluate_candidates(
            ranked_hypotheses=self.hyps,
            budget=self.budget,
            executed_ops=executed,
        )
        actions = [e.action for e in estimates]
        self.assertNotIn(DSLOperationName.COMPARE_WINDOWS, actions)
        self.assertNotIn(DSLOperationName.RUN_PELT, actions)

    def test_recoverability_model_penalizes_irreversible_close(self):
        close_penalty = ActionRecoverabilityModel.get_recoverability_penalty(InvestigationDecision.CLOSE)
        watch_penalty = ActionRecoverabilityModel.get_recoverability_penalty(InvestigationDecision.WATCH)
        self.assertGreater(close_penalty, watch_penalty)


if __name__ == "__main__":
    unittest.main()
