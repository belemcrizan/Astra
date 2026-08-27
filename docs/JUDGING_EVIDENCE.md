# ASTRA v0.3 — Hackathon Judging Evidence Matrix

This matrix maps ASTRA v0.3 features and architectural components to the official evaluation criteria.

---

| Criterion & Weight | Core ASTRA Capability | Direct Implementation Evidence | Verification Command |
|---|---|---|---|
| **Innovation & Operational Utility (40%)** | **Autonomous Investigation Loop** | Investigation transitions through `OBSERVING` $\rightarrow$ `TRIAGING` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `DECISION_READY` $\rightarrow$ `ESCALATED/CLOSED`. | `python -m astra_poc judge-demo` |
| **Innovation & Operational Utility (40%)** | **Discriminative Evidence Selection** | `DiscriminativeEvidenceSelector` chooses tests based on expected information value relative to cost ($E[I]/C$). | `python -m unittest tests.test_evidence_acquisition` |
| **Innovation & Operational Utility (40%)** | **Falsification & Changing Mind** | In the hero scenario, ASTRA begins with $H_1$ (noise) as the lead, falsifies it via PELT/Window contrast, and re-ranks $H_2/H_3$ as the winner. | `python -m astra_poc hero-demo` |
| **Innovation & Operational Utility (40%)** | **Benign Noise Safe Closure** | In the control scenario, routine fluctuations are investigated and closed safely without false alarms. | `python -m astra_poc control-demo` |
| **Architectural Discipline (30%)** | **Formal State Machine** | `InvestigationStateMachine` with explicit valid transition table and safe rejection of illegal jumps. | `python -m unittest tests.test_state_machine` |
| **Architectural Discipline (30%)** | **Restricted DSL Execution Boundary** | `DSLValidator` and `DSLExecutor` enforce strict parameter schemas and reject code injection attempts. | `python -m unittest tests.test_dsl_and_security` |
| **Architectural Discipline (30%)** | **Fault Handling & Failure Injection** | 5 controlled fault scenarios (injection, out-of-bounds, budget exhaustion, illegal transition, duplicate event). | `python -m astra_poc demo-failures` |
| **Architectural Discipline (30%)** | **Structured Telemetry & Audit Trail** | Every step logs trace ID, span ID, component, state, action, cost, and latency to JSONL and Markdown. | `artifacts/runs/` and `artifacts/reports/` |
| **Scientific Rigor & Reproducibility** | **Dual Track Isolation (Track A vs B)** | Track A (Controlled synthetic with ground truth) is strictly isolated from Track B (Real dataset empirical observation). | `python -m astra_poc real-demo` |
| **Scientific Rigor & Reproducibility** | **Preregistered 95% Wilson CIs** | All benchmark proportions report exact Wilson 95% confidence intervals; SHA-256 hash in every report. | `python -m astra_poc benchmark --seeds 30` |
| **Demo & Cloud Readiness (30%)** | **One-Command Cloud Run Deployment** | Multi-stage `Dockerfile`, `cloudbuild.yaml`, and deployment scripts with health check. | `deploy/README.md` |
| **Demo & Cloud Readiness (30%)** | **Local Fast Execution** | Full judge demo executes locally in <2 seconds with rich terminal telemetry. | `python -m astra_poc judge-demo` |

---

## Evaluation Alignment

- **Best Architectural Design**: Clean separation of state, hypotheses, evidence, DSL sandbox, decision policy, and telemetry.
- **Collaborative Partner (HITL)**: Full human review package generated whenever uncertainty remains or governance policies apply.
- **Individual / Solo Build**: Fully reproducible local test suite and clean CLI with zero cloud lock-in.
- **Grand Prize**: Measurable autonomous utility combined with rigorous scientific honesty.
