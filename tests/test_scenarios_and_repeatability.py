"""Tests for Canonical Scenario Registry, Repeatability, and Belief Delta Tracking in ASTRA v0.4.2."""

import unittest
from astra_poc.contracts import InvestigationDecision, StopReason
from astra_poc.google_agent import ASTRAInvestigationAgent
from astra_poc.scenarios.registry import ScenarioRegistry


class ScenarioAndRepeatabilityTests(unittest.IsolatedAsyncioTestCase):
    def test_scenario_registry_metadata_and_generation(self):
        """Registry: All canonical scenarios exist, have metadata, and generate valid arrays."""
        scenarios = ScenarioRegistry.list_scenarios()
        self.assertGreaterEqual(len(scenarios), 7)
        ids = [s.id for s in scenarios]
        for expected in ["hero", "control", "unknown", "budget", "adversarial", "multimodal", "real_world"]:
            self.assertIn(expected, ids)

        hero = ScenarioRegistry.generate("hero")
        self.assertEqual(hero.family, "C")
        self.assertEqual(len(hero.returns), 1200)

        unknown = ScenarioRegistry.generate("unknown")
        self.assertEqual(unknown.family, "H")
        self.assertEqual(len(unknown.returns), 1200)

    async def test_hypothesis_delta_accounting(self):
        """Audit: Provenance records contain structured hypothesis delta records."""
        agent = ASTRAInvestigationAgent(max_turns=3)
        hero = ScenarioRegistry.generate("hero")
        rep = await agent.run_investigation(
            returns=hero.returns,
            anomaly_idx=hero.anomaly_index,
            case_id="test-delta-hero",
        )
        self.assertGreaterEqual(len(rep.provenance_records), 1)
        prov = rep.provenance_records[0]
        self.assertGreaterEqual(len(prov.hypothesis_deltas), 4)
        
        # Verify delta record schema
        d0 = prov.hypothesis_deltas[0]
        self.assertIsNotNone(d0.hypothesis_id)
        self.assertIsNotNone(d0.score_before)
        self.assertIsNotNone(d0.score_after)
        self.assertIn(d0.direction, ["SUPPORTS", "CONTRADICTS", "NEUTRAL"])

    async def test_candidate_voi_utilities_captured(self):
        """VoI: Provenance records capture multi-attribute VoI utility rankings."""
        agent = ASTRAInvestigationAgent(max_turns=2)
        control = ScenarioRegistry.generate("control")
        rep = await agent.run_investigation(
            returns=control.returns,
            anomaly_idx=control.anomaly_index,
            case_id="test-voi-control",
        )
        self.assertGreaterEqual(len(rep.candidate_utilities), 1)
        u0 = rep.candidate_utilities[0]
        self.assertIn("operation", u0)
        self.assertIn("eig", u0)
        self.assertIn("efg", u0)
        self.assertIn("cost", u0)
        self.assertIn("voi", u0)

    async def test_repeatability_on_canonical_scenarios(self):
        """Repeatability: Hero, Control, and Unknown produce deterministic decisions over 3 trials."""
        agent = ASTRAInvestigationAgent(max_turns=3)
        
        # Test Hero -> ESCALATE
        hero = ScenarioRegistry.generate("hero")
        for i in range(3):
            rep = await agent.run_investigation(hero.returns, hero.anomaly_index, f"rep-hero-{i}")
            self.assertEqual(rep.decision, InvestigationDecision.ESCALATE)

        # Test Control -> CLOSE
        control = ScenarioRegistry.generate("control")
        for i in range(3):
            rep = await agent.run_investigation(control.returns, control.anomaly_index, f"rep-ctrl-{i}")
            self.assertEqual(rep.decision, InvestigationDecision.CLOSE)

        # Test Unknown -> DEFER
        unknown = ScenarioRegistry.generate("unknown")
        for i in range(3):
            rep = await agent.run_investigation(unknown.returns, unknown.anomaly_index, f"rep-unk-{i}")
            self.assertEqual(rep.decision, InvestigationDecision.DEFER)
            self.assertEqual(rep.stop_reason, StopReason.UNKNOWN_DOMINANT)


if __name__ == "__main__":
    unittest.main()
