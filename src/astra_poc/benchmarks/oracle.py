from __future__ import annotations

from typing import Any
from ..contracts import InvestigationDecision
from .scenarios import BenchmarkScenario


class PrivilegedOracle:
    """Privileged Oracle Upper-Bound Benchmark.
    
    Uses hidden generative ground truth to determine optimal minimal test selection
    and calculate exact decision and cost regret for autonomous policies.
    """

    @classmethod
    def evaluate_optimal_decision(cls, scenario: BenchmarkScenario) -> tuple[InvestigationDecision, float, int]:
        """Returns (optimal_decision, minimal_cost_units, minimal_tests)."""
        if scenario.family == "A":  # Transient noise
            # Optimal: 1 cheap contrast test (cost: 1.0) and CLOSE
            return InvestigationDecision.CLOSE, 1.0, 1
        elif scenario.family in ("B", "C"):  # Regime change / Structural break
            # Optimal: 1 exact PELT test (cost: 2.0) and ESCALATE
            return InvestigationDecision.ESCALATE, 2.0, 1
        elif scenario.family == "D":  # Coordinated weak signal
            # Optimal: 1 Stacking test (cost: 2.5) and ESCALATE
            return InvestigationDecision.ESCALATE, 2.5, 1
        elif scenario.family == "H":  # Open set / unknown
            # Optimal: 1 Entropy test (cost: 0.5) and DEFER
            return InvestigationDecision.DEFER, 0.5, 1
        else:
            return InvestigationDecision.ESCALATE, 2.0, 1

    @classmethod
    def calculate_regret(
        cls,
        scenario: BenchmarkScenario,
        policy_decision: InvestigationDecision,
        policy_cost: float,
        policy_tests: int,
    ) -> dict[str, float]:
        opt_dec, opt_cost, opt_tests = cls.evaluate_optimal_decision(scenario)

        # Decision match score
        is_correct = (policy_decision == opt_dec) or (policy_decision in scenario.acceptable_alternatives)
        decision_loss = 0.0 if is_correct else 10.0
        cost_regret = max(0.0, policy_cost - opt_cost)
        test_count_regret = max(0, policy_tests - opt_tests)

        return {
            "is_correct_resolution": 1.0 if is_correct else 0.0,
            "decision_loss": decision_loss,
            "cost_regret": round(cost_regret, 2),
            "test_count_regret": float(test_count_regret),
            "oracle_optimal_cost": opt_cost,
        }
