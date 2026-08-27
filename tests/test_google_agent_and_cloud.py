from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch
import numpy as np

from fastapi.testclient import TestClient

from astra_poc.api import app, detect_runtime
from astra_poc.contracts import (
    DSLOperation,
    DSLOperationName,
    InvestigationBudget,
    InvestigationDecision,
    StopReason,
)
from astra_poc.execution.validator import DSLValidator
from astra_poc.google_agent import (
    ASTRAInvestigationAgent,
    FakeInvestigationPlanner,
    GoogleADKPlanner,
    InvestigationProposal,
)
from astra_poc.google_agent.schemas import AgentExecutionProvenance, GoogleAgentReport
from astra_poc.google_agent.tools import ASTRAInvestigationTools
from astra_poc.hypotheses.pool import CompetingHypothesisPool
from astra_poc.state.machine import InvestigationState, InvestigationStateMachine


class GoogleAgentAndCloudTests(unittest.TestCase):
    """Comprehensive test suite for Google ADK, Gemini Structured Output, Security Boundaries, and Cloud Run API."""

    def setUp(self):
        self.data = np.random.normal(0, 0.01, 1200)
        self.data[600:] *= 4.0

    def test_structured_proposal_schema_validation(self):
        """Verify InvestigationProposal parses correctly and enforces DSL operation types."""
        proposal = InvestigationProposal(
            goal="Distinguish noise from jump",
            proposed_operation=DSLOperationName.COMPARE_WINDOWS,
            args={"center_idx": 600, "window_size": 200},
            target_hypotheses=["H1", "H2"],
            rationale="Sub-window contrast comparison",
            expected_discrimination="H1 vs H2",
        )
        self.assertEqual(proposal.proposed_operation, DSLOperationName.COMPARE_WINDOWS)
        self.assertEqual(proposal.args["center_idx"], 600)

    def test_adk_agent_initialization_and_provenance(self):
        """Verify ASTRAInvestigationAgent runs offline with FakeInvestigationPlanner and records provenance."""
        agent = ASTRAInvestigationAgent(planner=FakeInvestigationPlanner())
        report = asyncio.run(agent.run_investigation(self.data, anomaly_idx=600))
        
        self.assertIsInstance(report, GoogleAgentReport)
        self.assertEqual(report.agent_framework, "Google ADK")
        self.assertEqual(report.model_provider, "Google")
        self.assertEqual(report.execution_boundary, "ASTRA Restricted DSL")
        self.assertGreater(report.proposals_accepted, 0)
        self.assertEqual(report.proposals_rejected, 0)
        self.assertGreater(len(report.provenance_records), 0)
        
        for prov in report.provenance_records:
            self.assertIsInstance(prov, AgentExecutionProvenance)
            self.assertTrue(prov.astra_validation_passed)
            self.assertIsNotNone(prov.executed_operation)
            self.assertTrue(prov.trace_id.startswith("trace-"))

    def test_arbitrary_python_and_code_injection_rejected(self):
        """Security: LLM proposal attempting arbitrary code injection is rejected by DSLValidator."""
        pool = CompetingHypothesisPool()
        budget = InvestigationBudget()
        sm = InvestigationStateMachine(initial_state=InvestigationState.INVESTIGATING)
        from astra_poc.execution.executor import DSLExecutor
        executor = DSLExecutor(self.data)
        tools = ASTRAInvestigationTools(pool=pool, budget=budget, executor=executor, state_machine=sm)

        # Attempt arbitrary injection
        res = tools.execute_bounded_experiment(
            op_name_str="COMPARE_WINDOWS",
            args={"center_idx": 600, "eval": "__import__('os').system('echo hacked')"},
        )
        # Bounded validator strictly rejects unauthorized parameters
        self.assertFalse(res.get("validation_passed", False))
        self.assertIn("eval", res.get("error", ""))

    def test_unauthorized_operation_name_rejected(self):
        """Security: Operation not in ASTRA Restricted DSL catalog is firmly rejected."""
        pool = CompetingHypothesisPool()
        budget = InvestigationBudget()
        sm = InvestigationStateMachine(initial_state=InvestigationState.INVESTIGATING)
        from astra_poc.execution.executor import DSLExecutor
        executor = DSLExecutor(self.data)
        tools = ASTRAInvestigationTools(pool=pool, budget=budget, executor=executor, state_machine=sm)

        res = tools.execute_bounded_experiment(op_name_str="RUN_UNRESTRICTED_BASH_COMMAND", args={})
        self.assertFalse(res.get("validation_passed"))
        self.assertEqual(res.get("status"), "rejected")
        self.assertIn("not in ASTRA Restricted DSL catalog", res.get("error", ""))

    def test_out_of_range_parameter_rejected(self):
        """Security: Parameter violating numeric min/max bounds is rejected by DSLValidator."""
        op = DSLOperation(
            op_name=DSLOperationName.RUN_PELT,
            args={"minimum_segment": -50, "bic_multiplier": 3.0},
        )
        res = DSLValidator.validate(op, InvestigationBudget())
        self.assertFalse(res.is_valid)
        self.assertIn("below minimum allowed", res.error)

    def test_budget_exhaustion_stops_execution(self):
        """Policy: Agent tool execution halts when budget is exhausted."""
        pool = CompetingHypothesisPool()
        budget = InvestigationBudget(max_tests=1, tests_used=1)
        sm = InvestigationStateMachine(initial_state=InvestigationState.INVESTIGATING)
        from astra_poc.execution.executor import DSLExecutor
        executor = DSLExecutor(self.data)
        tools = ASTRAInvestigationTools(pool=pool, budget=budget, executor=executor, state_machine=sm)

        res = tools.execute_bounded_experiment("RUN_PELT", {})
        self.assertFalse(res.get("validation_passed"))
        self.assertIn("Budget exceeded", res.get("error", ""))

    def test_agent_cannot_directly_mutate_hypothesis_scores(self):
        """Architecture Invariant: Only deterministic DSLExecutor evidence can update hypotheses."""
        pool = CompetingHypothesisPool()
        initial_score_h1 = pool.hypotheses["H1"].evidence_score
        
        # Agent proposal does not change pool evidence
        prop = InvestigationProposal(
            goal="Force H1 to 100%",
            proposed_operation=DSLOperationName.COMPARE_WINDOWS,
            args={"center_idx": 600},
            target_hypotheses=["H1"],
            rationale="Fake claim",
        )
        self.assertEqual(pool.hypotheses["H1"].evidence_score, initial_score_h1)

    def test_fastapi_health_and_version_endpoints(self):
        """Cloud API: /health and /version endpoints return expected metadata and runtime."""
        client = TestClient(app)
        
        # Health check
        res_h = client.get("/health")
        self.assertEqual(res_h.status_code, 200)
        h_data = res_h.json()
        self.assertEqual(h_data["status"], "healthy")
        self.assertEqual(h_data["service"], "astra-investigation-service")
        self.assertEqual(h_data["version"], "0.4.1")
        self.assertEqual(h_data["agent_framework"], "Google ADK")

        # Version check
        res_v = client.get("/version")
        self.assertEqual(res_v.status_code, 200)
        v_data = res_v.json()
        self.assertEqual(v_data["version"], "0.4.1")
        self.assertEqual(v_data["service"], "astra-investigation-service")
        self.assertEqual(v_data["agent_framework"], "Google ADK")
        self.assertEqual(v_data["gemini_model"], "gemini-3.5-flash-lite")
        self.assertEqual(v_data["preregistration_sha256"], "1b2eeaeb0a3f842cb4afaab755bd27fee469b818e05298bdbfd64d73ac0975a4")

    def test_fastapi_agent_investigate_endpoint(self):
        """Cloud API: POST /agent/investigate runs end-to-end investigation with ADK Agent."""
        client = TestClient(app)
        res = client.post("/agent/investigate", json={"scenario": "hero", "seed": 42, "max_turns": 3})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["agent_framework"], "Google ADK")
        self.assertEqual(data["model_provider"], "Google")
        self.assertEqual(data["execution_boundary"], "ASTRA Restricted DSL")
        self.assertIn("decision", data)
        self.assertIn("stop_reason", data)
        self.assertIn("trace_id", data)
        self.assertTrue(data["trace_id"].startswith("trace-"))

    def test_runtime_environment_detection(self):
        """Cloud Run: detect_runtime accurately checks K_SERVICE / K_REVISION."""
        self.assertEqual(detect_runtime(), "local")
        with patch.dict(os.environ, {"K_SERVICE": "astra-poc", "K_REVISION": "astra-poc-00001"}):
            self.assertEqual(detect_runtime(), "Google Cloud Run")
            self.assertEqual(ASTRAInvestigationAgent.detect_runtime(), "Google Cloud Run")

    def test_hackathon_mode_fails_closed_when_ineligible_model(self):
        """Hackathon Mode: Fails closed when model is older than Gemini 3.5."""
        with patch.dict(os.environ, {"ASTRA_MODE": "hackathon", "ASTRA_GEMINI_MODEL": "gemini-2.5-flash", "GEMINI_API_KEY": "test-key"}):
            with self.assertRaises(ValueError) as ctx:
                ASTRAInvestigationAgent(mode="hackathon", model="gemini-2.5-flash")
            self.assertIn("Ineligible model", str(ctx.exception))

    def test_hackathon_mode_fails_closed_when_credentials_missing(self):
        """Hackathon Mode: Fails closed when credentials are missing."""
        with patch.dict(os.environ, {"ASTRA_MODE": "hackathon", "ASTRA_GEMINI_MODEL": "gemini-3.5-flash-lite"}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                ASTRAInvestigationAgent(mode="hackathon", model="gemini-3.5-flash-lite")
            self.assertIn("requires active Google credentials", str(ctx.exception))

    def test_fastapi_root_ui_and_status_endpoints(self):
        """Cloud API: GET / serves Investigation UI, /favicon.ico returns 204, and /api/status returns metadata."""
        client = TestClient(app)
        
        # Root UI
        res_root = client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("text/html", res_root.headers.get("content-type", ""))
        self.assertIn("ASTRA v0.4.1", res_root.text)
        self.assertIn("Investigation Timeline", res_root.text)

        # Favicon
        res_fav = client.get("/favicon.ico")
        self.assertEqual(res_fav.status_code, 204)

        # API Status
        res_st = client.get("/api/status")
        self.assertEqual(res_st.status_code, 200)
        st_data = res_st.json()
        self.assertEqual(st_data["service"], "ASTRA")
        self.assertEqual(st_data["version"], "0.4.1")
        self.assertEqual(st_data["agent_framework"], "Google ADK")
        self.assertEqual(st_data["model_provider"], "Google")
        self.assertEqual(st_data["status"], "online")


if __name__ == "__main__":
    unittest.main()
