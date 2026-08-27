from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import numpy as np

from astra_poc.agents import normalized_correlation, robust_zscore
from astra_poc.baselines import pelt_baseline
from astra_poc.config import Settings
from astra_poc.contracts import AgentStatus, InvestigationReport
from astra_poc.datasets import generate_synthetic_market
from astra_poc.evaluation import evaluate_detections, match_detections, wilson_interval
from astra_poc.orchestrator import OrchestratorAgent
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

    def test_stacking_uses_reproducible_temporal_null(self):
        data = generate_synthetic_market(2400, 42)
        config = PREREGISTRATION["stacking"]
        first = event_stacking_test(data.returns, data.event_indicator, data.template, permutations=config["permutations"], alpha=config["alpha"], seed=42)
        second = event_stacking_test(data.returns, data.event_indicator, data.template, permutations=config["permutations"], alpha=config["alpha"], seed=42)
        self.assertEqual(first.p_value, second.p_value)
        self.assertEqual(first.null_method, "circular_time_shift")
        self.assertFalse(first.significant)

    def test_stacking_does_not_claim_zero_signal_for_reference_seed(self):
        data = generate_synthetic_market(2400, 42, signal_amplitude=0.0)
        config = PREREGISTRATION["stacking"]
        result = event_stacking_test(data.returns, data.event_indicator, data.template, permutations=config["permutations"], alpha=config["alpha"], seed=42)
        self.assertFalse(result.significant)

    def test_preregistration_has_stable_sha256_identity(self):
        self.assertEqual(len(preregistration_hash()), 64)
        self.assertEqual(preregistration_hash(), preregistration_hash())


class EndToEndTests(unittest.TestCase):
    def test_investigation_is_observable_and_reports_full_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(seed=42, points=2400, output_dir=Path(directory))
            report = asyncio.run(OrchestratorAgent(settings).investigate())
            self.assertTrue(report.correlation_id)
            self.assertEqual(report.metrics["agents_failed"], 0)
            self.assertTrue(all(agent.status == AgentStatus.COMPLETED for agent in report.agents))
            regime = report.scientific_evaluation["regime_metrics"]
            self.assertEqual(regime["precision"], 1.0)
            self.assertEqual(regime["recall"], 1.0)
            self.assertEqual(regime["f1"], 1.0)
            self.assertIn("precision_ci95", regime)
            self.assertIn("mean_absolute_delay", regime)
            self.assertIn("PELT-Gaussian", report.scientific_evaluation["baselines"])
            h2 = next(h for h in report.hypotheses if h.hypothesis_id == "H2")
            self.assertIn(h2.falsification_status, ("challenged", "active", "leading", "confirmed", "falsified"))
            self.assertTrue((Path(directory) / "runs" / f"{report.run_id}.jsonl").exists())
            self.assertTrue((Path(directory) / "reports" / f"{report.run_id}.md").exists())

    def test_schema_uses_evidence_score_not_confidence(self):
        schema = str(InvestigationReport.model_json_schema())
        self.assertIn("evidence_score", schema)
        self.assertNotIn("'confidence'", schema)


if __name__ == "__main__":
    unittest.main()
