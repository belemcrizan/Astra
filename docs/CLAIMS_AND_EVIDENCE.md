# ASTRA Claims and Evidence Alignment Matrix

This matrix explicitly aligns every architectural, scientific, operational, and Google Hackathon claim made by ASTRA with concrete code artifacts, test suites, and reproduction commands.

---

| Architectural / Technology Claim | Implementation Artifact | Automated Test | Reproduction Command |
| :--- | :--- | :--- | :--- |
| **Google Agent Framework (ADK 2.8.0)** | `src/astra_poc/google_agent/agent.py`, `tools.py` | `tests/test_google_agent_and_cloud.py` | `python -m astra_poc google-agent-demo` |
| **Gemini 3.5+ Investigation Planning** | `src/astra_poc/google_agent/agent.py`, `schemas.py` | `tests/test_google_agent_and_cloud.py` | `python -m astra_poc integration-test-google` |
| **Google Cloud Run Deployment & Runtime Detection** | `src/astra_poc/api.py`, `deploy/deploy_cloud_run.sh` | `tests/test_google_agent_and_cloud.py` | `python -m astra_poc cloud-verify --url <URL>` |
| **Bounded Investigation State Machine** | `src/astra_poc/state/machine.py` | `tests/test_state_machine.py` | `python -m astra_poc judge-demo` |
| **Restricted Sandboxed DSL** | `src/astra_poc/execution/dsl.py`, `executor.py`, `validator.py` | `tests/test_dsl_and_security.py` | `python -m astra_poc schema` |
| **Falsification-First & Change of Mind** | `src/astra_poc/hypotheses/pool.py`, `engine.py` | `tests/test_hypotheses_and_falsification.py` | `python -m astra_poc hero-demo` |
| **Safe Closure of Benign Fluctuation** | `src/astra_poc/policy/stopping.py`, `decision.py` | `tests/test_v04_1_validation.py` | `python -m astra_poc control-demo` |
| **Open-Set Refusal ($H_{\text{unknown}}$)** | `src/astra_poc/hypotheses/pool.py`, `stopping.py` | `tests/test_unknown_and_openset.py` | `python -m astra_poc unknown-demo` |
| **Budget-Adaptive Depth & Stopping** | `src/astra_poc/policy/stopping.py`, `contracts.py` | `tests/test_v04_1_validation.py` | `python -m astra_poc budget-demo` |
| **Value of Information (VoI / EIG / EFG)** | `src/astra_poc/policy/voi.py` | `tests/test_policy_and_voi.py` | `python -m astra_poc judge-demo` |
| **Multi-Tenant Fleet Isolation** | `src/astra_poc/fleet/isolation.py`, `locks.py` | `tests/test_fleet_and_concurrency.py` | `python -m unittest tests/test_fleet_and_concurrency.py` |
| **Cryptographic Provenance Graph & Chains** | `src/astra_poc/provenance/graph.py`, `chain.py` | `tests/test_provenance_and_integrity.py` | `python -m astra_poc judge-demo` |
| **Sandboxed Multimodal Cross-Check** | `src/astra_poc/adapters/base.py`, `multimodal/adapter.py` | `tests/test_multimodal.py` | `python -m astra_poc multimodal-demo` |
| **Scientific Benchmark & Pareto Frontier** | `src/astra_poc/benchmarks/runner.py`, `scenarios.py` | `tests/test_benchmarks_and_pareto.py` | `python -m astra_poc pareto-frontier` |
| **Separate Empirical Track B (No Fake Ground Truth)** | `src/astra_poc/adapters/real_market.py` | `tests/test_v04_1_validation.py` | `python -m astra_poc real-demo` |
| **Methodological Preregistration Identity** | `src/astra_poc/preregistration.py` | `tests/test_scientific_kernel.py` | `python -m astra_poc preregistration` |
