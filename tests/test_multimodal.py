from __future__ import annotations

import unittest
import numpy as np
from astra_poc.multimodal.adapter import MultimodalEvidenceAdapter


class MultimodalTests(unittest.TestCase):
    def test_multimodal_ingestion_and_cross_check(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0001, 0.007, 1200)
        # Inject variance regime jump at t=700
        returns[700:] *= 3.0

        claim = MultimodalEvidenceAdapter.ingest_document_or_chart(
            file_path="mock_chart.png",
            claim_statement="Chart shows volatility surge at t=700.",
            claimed_timestamp=700,
        )
        self.assertEqual(claim.verification_status, "unverified")
        self.assertIsNotNone(claim.source_hash)

        updated_claim, ev_item = MultimodalEvidenceAdapter.cross_check_claim(claim, returns)
        self.assertEqual(updated_claim.verification_status, "verified_consistent")
        self.assertTrue(ev_item.passed)
        self.assertIn("MULTIMODAL_CROSS_CHECK", ev_item.code)


if __name__ == "__main__":
    unittest.main()
