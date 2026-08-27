# ASTRA v0.4 — Hackathon Judging Evidence Matrix

This matrix maps ASTRA v0.4 features and scientific components to the official evaluation criteria and prize categories.

---

## Evaluation Criteria Mapping

| Criterion & Category | Core ASTRA Capability | Direct Implementation Evidence | Verification Command |
|---|---|---|---|
| **Innovation & Operational Utility (40%)** | **Adaptive Value of Information (VoI)** | `VoIEngine` calculates $U(a) = \alpha \cdot \text{EIG} + \beta \cdot \text{EFG} + \gamma \cdot \text{EDR} - \lambda_c C - \lambda_t T - \lambda_r R$ and stops when $\text{VoI} \le 0$. | `python -m astra_poc judge-demo --explain-policy` |
| **Innovation & Operational Utility (40%)** | **Functional Open-Set ($H_{\text{unknown}}$)** | Unmodeled dynamics elevate $H_{\text{unknown}}$, refusing forced classification and proposing hypothesis expansions. | `python -m astra_poc unknown-demo` |
| **Innovation & Operational Utility (40%)** | **Quality-Cost Pareto Dominance** | Benchmark proves ASTRA Adaptive policy dominates Fixed-Sequence and Falsification-Only baselines on the Pareto curve. | `python -m astra_poc pareto-frontier` |
| **Architectural Discipline (30%)** | **Decision Provenance Graph (DAG)** | Generates formal DAGs connecting observations $\rightarrow$ hypotheses $\rightarrow$ actions $\rightarrow$ evidence $\rightarrow$ falsification $\rightarrow$ decisions in Mermaid and JSON. | `python -m astra_poc judge-demo` |
| **Architectural Discipline (30%)** | **Multi-Case Fleet Isolation** | `CaseIsolationManager` and `OptimisticCaseLock` enforce tenant boundaries, lease tokens, and prevent stale version mutations. | `python -m unittest tests.test_fleet_and_concurrency` |
| **Architectural Discipline (30%)** | **Tamper-Evident Hashing & Replay** | Cryptographic SHA-256 event chaining ($H_t = \text{SHA256}(H_{t-1} \parallel \text{event}_t)$) and deterministic replayer. | `python -m astra_poc replay <report>` |
| **Scientific Rigor & Reproducibility** | **10-Family Investigation Benchmark** | Evaluates 10 scenario families (Noise, Drift, Break, Signal, Mixed, Conflicting, Missing, Open-Set, Adversarial, Ambiguous). | `python -m astra_poc benchmark --seeds 30` |
| **Scientific Rigor & Reproducibility** | **Privileged Oracle & Regret Tracking** | Calculates Decision Regret and Cost Regret against an optimal oracle upper bound. | `python -m unittest tests.test_benchmarks_and_pareto` |
| **Demo & Cloud Readiness (30%)** | **Local Fast Execution & Cloud Run** | Judge demo runs in $<2$ seconds locally; multi-stage Dockerfile and deployment scripts verified for Cloud Run. | `python -m astra_poc judge-demo` |

---

## Award Alignment Self-Audit

- **Grand Prize Coherence**: Unifies detection, competing hypotheses, rational test selection, falsification, open-set recognition, explicit stopping, counterfactuals, and tamper-evident auditability into a single coherent narrative.
- **Fortified Enterprise Fleet**: Demonstrates multi-case isolation, tenant boundary enforcement, lease locks, policy versioning, and crash recovery.
- **Best Architectural Design**: Clean separation of state machine, decision utility, restricted execution sandbox, hypothesis pool, and provenance DAGs.
- **Collaborative Partner (HITL)**: Full human review packages, selective risk-coverage thresholds, and sandboxed multimodal cross-checking for analyst artifacts.
- **Individual / Solo Build**: Fully reproducible local test suite (58 unit tests passing) with zero mandatory cloud dependencies.
