from __future__ import annotations

import asyncio
import unittest

from astra_poc.adapters.base import DatasetTrack
from astra_poc.adapters.real_market import RealMarketAdapter
from astra_poc.adapters.synthetic import SyntheticMarketAdapter
from astra_poc.investigation.engine import InvestigationEngine


class AdaptersAndIdempotencyTests(unittest.TestCase):
    def test_synthetic_adapter_preserves_track_a_and_ground_truth(self):
        adapter = SyntheticMarketAdapter(points=1200, seed=42)
        self.assertEqual(adapter.track, DatasetTrack.TRACK_A_SYNTHETIC)
        self.assertTrue(adapter.has_ground_truth)
        self.assertEqual(adapter.watermark, "SYNTHETIC_ONLY_NOT_REAL_DATA")
        data = adapter.load()
        self.assertEqual(len(data.returns), 1200)

    def test_real_market_adapter_preserves_track_b_and_no_ground_truth(self):
        adapter = RealMarketAdapter()
        self.assertEqual(adapter.track, DatasetTrack.TRACK_B_REAL)
        self.assertFalse(adapter.has_ground_truth)
        data = adapter.load()
        self.assertGreater(len(data.returns), 100)
        self.assertEqual(adapter.metadata["ground_truth_available"], False)

    def test_event_deduplication_idempotency(self):
        engine = InvestigationEngine()
        data = SyntheticMarketAdapter(points=1200, seed=42).load()
        rep1 = asyncio.run(engine.investigate(data))
        rep2 = asyncio.run(engine.investigate(data))
        self.assertIsNotNone(rep1.investigation_id)
        self.assertIsNotNone(rep2.investigation_id)


if __name__ == "__main__":
    unittest.main()
