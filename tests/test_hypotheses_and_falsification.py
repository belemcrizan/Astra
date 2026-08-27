from __future__ import annotations

import unittest

from astra_poc.contracts import HypothesisStatus
from astra_poc.execution.executor import DSLExecutor
from astra_poc.falsification.engine import FalsificationEngine
from astra_poc.hypotheses.pool import HypothesisPool, create_standard_hypothesis_pool


class HypothesesAndFalsificationTests(unittest.TestCase):
    def test_pool_initialization_contains_all_hypotheses(self):
        pool = HypothesisPool()
        hypotheses = pool.all()
        self.assertEqual(len(hypotheses), 5)
        h_ids = {h.id for h in hypotheses}
        self.assertEqual(h_ids, {"H1", "H2", "H3", "H4", "H_unknown"})

    def test_evidence_update_modifies_rank_and_status(self):
        pool = HypothesisPool()
        h3 = pool.update_evidence("H3", delta=+0.35, supporting_msg="Confirmed by PELT")
        self.assertEqual(h3.status, HypothesisStatus.CONFIRMED)
        self.assertEqual(pool.get_leading().id, "H3")

    def test_falsification_first_mind_changing_scenario(self):
        # Scenario: Start with H1 as leading, run targeted adversarial test, falsify H1, promote H3
        pool = HypothesisPool()
        # Initial lead is H1
        self.assertEqual(pool.get_leading().id, "H1")

        # Falsify H1
        pool.record_falsification_attempt(
            "H1",
            test_name="COMPARE_WINDOWS",
            falsified=True,
            details={"contrast_score": 1.85},
        )
        self.assertEqual(pool.get("H1").status, HypothesisStatus.FALSIFIED)
        self.assertNotEqual(pool.get_leading().id, "H1")

        # Support H3
        pool.update_evidence("H3", delta=+0.30, supporting_msg="PELT boundary confirmed at t=720")
        self.assertEqual(pool.get_leading().id, "H3")


if __name__ == "__main__":
    unittest.main()
