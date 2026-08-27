from __future__ import annotations

import unittest
from astra_poc.contracts import HypothesisStatus, InvestigationDecision, InvestigationHypothesis, StopReason
from astra_poc.hypotheses.pool import CompetingHypothesisPool
from astra_poc.policy.decision import InvestigationPolicy
from astra_poc.contracts import InvestigationBudget


class UnknownAndOpenSetTests(unittest.TestCase):
    def test_unknown_score_elevates_when_all_known_falsified(self):
        pool = CompetingHypothesisPool()
        # Falsify H1, H2, H3, H4
        pool.update_evidence("RUN_PELT", supports=[], contradicts=["H1"], evidence_delta=0.30)
        pool.update_evidence("CHECK_SUSCEPTIBILITY", supports=[], contradicts=["H2"], evidence_delta=0.30)
        pool.update_evidence("RUN_BOCPD", supports=[], contradicts=["H3"], evidence_delta=0.30)
        pool.update_evidence("TEST_TEMPORAL_STACKING", supports=[], contradicts=["H4"], evidence_delta=0.30)

        self.assertGreaterEqual(pool.unknown_score, 0.60)
        ranked = pool.get_ranked_hypotheses()
        self.assertEqual(ranked[0].id, "H_unknown")
        self.assertIn("Unmodeled Exogenous Jump-Diffusion Dynamics", pool.hypothesis_expansion_proposals)

    def test_policy_refuses_forced_classification_when_unknown_dominant(self):
        pool = CompetingHypothesisPool()
        pool.unknown_score = 0.75
        pool.hypotheses["H_unknown"].evidence_score = 0.75
        for hid in ["H1", "H2", "H3", "H4"]:
            pool.hypotheses[hid].evidence_score = 0.10
            pool.hypotheses[hid].status = HypothesisStatus.FALSIFIED

        policy = InvestigationPolicy(unknown_threshold=0.60)
        outcome = policy.evaluate(pool.get_ranked_hypotheses(), InvestigationBudget(), unknown_score=0.75)
        self.assertEqual(outcome.decision, InvestigationDecision.DEFER)
        self.assertEqual(outcome.stop_reason, StopReason.UNKNOWN_DOMINANT)
        self.assertTrue(outcome.human_review_required)


if __name__ == "__main__":
    unittest.main()
