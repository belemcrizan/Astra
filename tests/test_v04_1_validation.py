from __future__ import annotations

import asyncio
import unittest

from astra_poc.adapters.real_market import RealMarketAdapter
from astra_poc.adapters.synthetic import SyntheticMarketAdapter
from astra_poc.benchmarks.scenarios import ScenarioGenerator
from astra_poc.contracts import (
    ActionUtilityEstimate,
    DSLOperationName,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationHypothesis,
    StopReason,
)
from astra_poc.investigation.engine import InvestigationEngine
from astra_poc.policy.stopping import StoppingPolicy
from astra_poc.policy.voi import VoIEngine


class V041CorrectiveValidationTests(unittest.TestCase):
    """Rigorous validation tests verifying all ASTRA v0.4.1 defect repairs."""

    def test_control_decision_consistency(self):
        """P0: Control scenario closes benign noise with DECISION_SUFFICIENT or EXPECTED_VOI_NON_POSITIVE."""
        scenario = ScenarioGenerator.generate_scenario("A", seed=999)
        engine = InvestigationEngine()
        rep = asyncio.run(engine.investigate(scenario, strategy="evidence_driven", force_reprocess=True))
        
        self.assertIsNotNone(rep.decision_outcome)
        self.assertEqual(rep.decision_outcome.decision, InvestigationDecision.CLOSE)
        self.assertIn(
            rep.stop_reason,
            (StopReason.DECISION_SUFFICIENT, StopReason.EXPECTED_VOI_NON_POSITIVE),
        )
        self.assertEqual(rep.competing_hypotheses[0].id, "H1")

    def test_unknown_dominance_and_openset(self):
        """P0: Open-set heavy-tailed dynamics elevate H_unknown and refuse forced classification."""
        scenario = ScenarioGenerator.generate_scenario("H", seed=101)
        engine = InvestigationEngine()
        rep = asyncio.run(engine.investigate(scenario, strategy="evidence_driven", force_reprocess=True))
        
        self.assertIsNotNone(rep.decision_outcome)
        self.assertEqual(rep.stop_reason, StopReason.UNKNOWN_DOMINANT)
        self.assertEqual(rep.decision_outcome.decision, InvestigationDecision.DEFER)
        self.assertGreaterEqual(rep.unknown_score, 0.60)

    def test_budget_sensitivity_and_adaptation(self):
        """P0: Material budget changes alter investigation depth and outcome."""
        scenario = ScenarioGenerator.generate_scenario("B", seed=42)
        engine = InvestigationEngine()

        b_low = InvestigationBudget(max_cost_units=1.0, max_steps=1, max_tests=1)
        rep_low = asyncio.run(engine.investigate(scenario, budget=b_low, force_reprocess=True))

        b_high = InvestigationBudget(max_cost_units=8.0, max_steps=6, max_tests=6)
        rep_high = asyncio.run(engine.investigate(scenario, budget=b_high, force_reprocess=True))

        self.assertNotEqual(rep_low.budget.steps_used, rep_high.budget.steps_used)
        self.assertGreater(rep_high.budget.cost_units_used, rep_low.budget.cost_units_used)
        self.assertEqual(rep_low.stop_reason, StopReason.BUDGET_EXHAUSTED)
        self.assertEqual(rep_high.stop_reason, StopReason.DECISION_SUFFICIENT)

    def test_stop_reason_invariants(self):
        """P0: BUDGET_EXHAUSTED occurs only when positive-VoI candidate tests are blocked by budget."""
        hyps = [
            InvestigationHypothesis(id="H1", name="Noise", evidence_score=0.45),
            InvestigationHypothesis(id="H2", name="Regime", evidence_score=0.40),
        ]
        b_exhausted = InvestigationBudget(max_steps=2, steps_used=2)
        estimates_positive = [ActionUtilityEstimate(action=DSLOperationName.RUN_PELT, voi=1.8, selected=True)]
        
        # When positive-VoI candidate exists and budget is exhausted -> BUDGET_EXHAUSTED
        _, reason_pos, _ = StoppingPolicy.evaluate_stop(
            ranked_hypotheses=hyps,
            utility_estimates=estimates_positive,
            budget=b_exhausted,
        )
        self.assertEqual(reason_pos, StopReason.BUDGET_EXHAUSTED)

        # When candidates are exhausted -> INFORMATION_EXHAUSTED
        _, reason_empty, _ = StoppingPolicy.evaluate_stop(
            ranked_hypotheses=hyps,
            utility_estimates=[],
            budget=b_exhausted,
        )
        self.assertEqual(reason_empty, StopReason.INFORMATION_EXHAUSTED)

    def test_action_utility_tie_breaking(self):
        """VoIEngine uses deterministic tie-breaking across runs."""
        hyps = [
            InvestigationHypothesis(id="H1", name="Noise", evidence_score=0.50),
            InvestigationHypothesis(id="H2", name="Regime", evidence_score=0.50),
        ]
        b = InvestigationBudget()
        
        est1 = VoIEngine.evaluate_candidates(hyps, b, set(), unknown_score=0.2)
        est2 = VoIEngine.evaluate_candidates(hyps, b, set(), unknown_score=0.2)
        
        self.assertEqual([e.action for e in est1], [e.action for e in est2])
        self.assertTrue(est1[0].selected)

    def test_real_market_adapter_contract(self):
        """RealMarketAdapter adheres to DatasetAdapter contract with has_ground_truth=False."""
        adapter = RealMarketAdapter()
        data = adapter.load()
        self.assertFalse(adapter.has_ground_truth)
        self.assertGreater(len(data.returns), 100)
        self.assertIsNotNone(data.sha256)


if __name__ == "__main__":
    unittest.main()
