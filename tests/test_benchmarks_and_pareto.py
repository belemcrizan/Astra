from __future__ import annotations

import unittest
from astra_poc.benchmarks.oracle import PrivilegedOracle
from astra_poc.benchmarks.pareto import ParetoFrontierAnalyzer
from astra_poc.benchmarks.scenarios import ScenarioGenerator
from astra_poc.contracts import InvestigationDecision


class BenchmarksAndParetoTests(unittest.TestCase):
    def test_scenario_generator_produces_all_families(self):
        for fam in ["A", "B", "C", "D", "H", "I"]:
            scen = ScenarioGenerator.generate_scenario(fam, seed=42)
            self.assertEqual(scen.family, fam)
            self.assertEqual(len(scen.returns), 1200)
            self.assertIsNotNone(scen.expected_decision)

    def test_oracle_regret_calculation(self):
        scen = ScenarioGenerator.generate_scenario("A", seed=42)
        # Policy matched oracle decision (CLOSE) but used 2 extra cost units
        regret = PrivilegedOracle.calculate_regret(
            scenario=scen,
            policy_decision=InvestigationDecision.CLOSE,
            policy_cost=3.0,
            policy_tests=3,
        )
        self.assertEqual(regret["is_correct_resolution"], 1.0)
        self.assertEqual(regret["cost_regret"], 2.0)
        self.assertEqual(regret["decision_loss"], 0.0)

    def test_pareto_frontier_identifies_non_dominated_points(self):
        runs = {
            "PolicyA": [{"is_correct": 1.0, "cost_units": 2.0, "latency_ms": 10.0, "cost_regret": 0.0}],
            "PolicyB": [{"is_correct": 0.5, "cost_units": 5.0, "latency_ms": 20.0, "cost_regret": 3.0}],
        }
        pareto = ParetoFrontierAnalyzer.evaluate_pareto_frontier(runs)
        self.assertEqual(len(pareto), 2)
        # PolicyA dominates PolicyB
        p_a = next(p for p in pareto if p["policy"] == "PolicyA")
        p_b = next(p for p in pareto if p["policy"] == "PolicyB")
        self.assertTrue(p_a["pareto_efficient"])
        self.assertFalse(p_b["pareto_efficient"])


if __name__ == "__main__":
    unittest.main()
