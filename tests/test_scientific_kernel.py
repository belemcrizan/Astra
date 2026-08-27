from __future__ import annotations

import unittest
import numpy as np

from astra_poc.agents import normalized_correlation, robust_zscore
from astra_poc.baselines import bocpd_baseline, cusum_baseline, page_hinkley_baseline, pelt_baseline
from astra_poc.datasets import generate_synthetic_market
from astra_poc.evaluation import evaluate_detections, match_detections, wilson_interval
from astra_poc.preregistration import PREREGISTRATION, preregistration_hash
from astra_poc.stacking import event_stacking_test


class ScientificKernelTests(unittest.TestCase):
    def test_robust_zscore_resists_outlier(self):
        values = np.array([0.0, 0.1, -0.1, 0.05, 9.0])
        self.assertGreater(robust_zscore(values)[-1], 20)

    def test_template_alignment_peaks_at_injection(self):
        template = np.array([-1.0, -0.5, 0.5, 1.0])
        values = np.zeros(30)
        values[12:16] = template
        self.assertEqual(int(np.argmax(normalized_correlation(values, template))), 12)

    def test_same_seed_reproduces_dataset_hash_and_watermark(self):
        first = generate_synthetic_market(1200, 7)
        second = generate_synthetic_market(1200, 7)
        np.testing.assert_allclose(first.returns, second.returns)
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.watermark, "SYNTHETIC_ONLY_NOT_REAL_DATA")

    def test_one_to_one_matching_penalizes_duplicate_alarm(self):
        pairs = match_detections([100], [99, 101], tolerance=3)
        metrics = evaluate_detections([100], [99, 101], tolerance=3, series_length=1000)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(metrics.true_positives, 1)
        self.assertEqual(metrics.false_positives, 1)
        self.assertEqual(metrics.precision, 0.5)

    def test_wilson_exposes_uncertainty_of_two_out_of_two(self):
        lower, upper = wilson_interval(2, 2)
        self.assertAlmostEqual(lower, 0.3424, places=3)
        self.assertEqual(upper, 1.0)

    def test_pelt_is_a_competitive_baseline(self):
        data = generate_synthetic_market(2400, 42)
        result = pelt_baseline(data.returns, **PREREGISTRATION["baselines"]["pelt"])
        metrics = evaluate_detections(data.regime_changes, result.change_points, 84, 2400)
        self.assertEqual(metrics.precision, 1.0)
        self.assertEqual(metrics.recall, 1.0)

    def test_bocpd_and_cusum_baselines(self):
        data = generate_synthetic_market(2400, 42)
        bocpd_res = bocpd_baseline(data.returns, **PREREGISTRATION["baselines"]["bocpd"])
        self.assertIsInstance(bocpd_res.change_points, list)
        cusum_res = cusum_baseline(data.returns, **PREREGISTRATION["baselines"]["cusum"])
        self.assertIsInstance(cusum_res.change_points, list)

    def test_stacking_uses_reproducible_temporal_null(self):
        data = generate_synthetic_market(2400, 42)
        config = PREREGISTRATION["stacking"]
        first = event_stacking_test(data.returns, data.event_indicator, data.template, permutations=config["permutations"], alpha=config["alpha"], seed=42)
        second = event_stacking_test(data.returns, data.event_indicator, data.template, permutations=config["permutations"], alpha=config["alpha"], seed=42)
        self.assertEqual(first.p_value, second.p_value)
        self.assertEqual(first.null_method, "circular_time_shift")

    def test_stacking_does_not_claim_zero_signal_for_reference_seed(self):
        data = generate_synthetic_market(2400, 42, signal_amplitude=0.0)
        config = PREREGISTRATION["stacking"]
        result = event_stacking_test(data.returns, data.event_indicator, data.template, permutations=config["permutations"], alpha=config["alpha"], seed=42)
        self.assertFalse(result.significant)

    def test_preregistration_has_stable_sha256_identity(self):
        self.assertEqual(len(preregistration_hash()), 64)
        self.assertEqual(preregistration_hash(), preregistration_hash())


if __name__ == "__main__":
    unittest.main()
