from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import numpy as np

from astra_poc.config import Settings
from astra_poc.contracts import InvestigationDecision, InvestigationReport, InvestigationState
from astra_poc.investigation.engine import InvestigationEngine


class EndToEndTests(unittest.TestCase):
    def test_investigation_is_observable_and_reports_full_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(seed=42, points=2400, output_dir=Path(directory))
            engine = InvestigationEngine(settings)
            report = asyncio.run(engine.investigate())

            self.assertTrue(report.correlation_id)
            self.assertTrue(report.investigation_id.startswith("inv-"))
            self.assertEqual(report.initial_state, InvestigationState.OBSERVING)
            self.assertIn(report.final_state, [InvestigationState.CLOSED, InvestigationState.WATCHING, InvestigationState.ESCALATED, InvestigationState.DEFERRED])
            self.assertGreater(len(report.state_history), 2)
            self.assertGreater(len(report.competing_hypotheses), 0)
            self.assertGreater(len(report.dsl_results), 0)
            self.assertIsNotNone(report.decision_outcome)
            
            # Check JSON & MD written
            json_file = Path(directory) / "reports" / f"{report.run_id}.json"
            md_file = Path(directory) / "reports" / f"{report.run_id}.md"
            self.assertTrue(json_file.exists())
            self.assertTrue(md_file.exists())

    def test_schema_uses_evidence_score_not_confidence(self):
        schema = str(InvestigationReport.model_json_schema())
        self.assertIn("evidence_score", schema)
        self.assertNotIn("'confidence'", schema)

    def test_control_scenario_closes_benign_noise_without_escalation(self):
        rng = np.random.default_rng(999)
        noise_returns = rng.normal(0.0001, 0.007, 1200)
        noise_returns[600] = 0.035
        price_arr = 100.0 * np.exp(np.cumsum(noise_returns))
        vol_arr = rng.lognormal(mean=11.0, sigma=0.2, size=1200)

        class BenignData:
            def __init__(self):
                self.returns = noise_returns
                self.price = price_arr
                self.volume = vol_arr
                self.time = np.arange(1200)
                self.seed = 999
                self.version = "benign-test-series"
                self.watermark = "SYNTHETIC_ONLY_NOT_REAL_DATA"
                self.sha256 = "benign-test-sha"

        engine = InvestigationEngine(Settings(points=1200, seed=999))
        report = asyncio.run(engine.investigate(BenignData(), force_reprocess=True))
        self.assertIn(report.decision_outcome.decision, [InvestigationDecision.CLOSE, InvestigationDecision.WATCH, InvestigationDecision.DEFER])
        self.assertNotEqual(report.decision_outcome.decision, InvestigationDecision.ESCALATE)


if __name__ == "__main__":
    unittest.main()
