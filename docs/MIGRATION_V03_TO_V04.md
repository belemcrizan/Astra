# ASTRA Migration Guide — v0.3 to v0.4

---

## 1. Summary of Changes

| Dimension | ASTRA v0.3 | ASTRA v0.4 |
|---|---|---|
| **Operational Control** | Autonomous investigation workflow. | **Rational Investigation Control & Decision Science** (evaluates expected utility $U(a)$ at every step). |
| **Stopping Policy** | Hard threshold or budget limit. | **Value of Information ($\text{VoI}$)** stopping: halts tests when expected utility gain $\le 0$. |
| **Open-Set ($H_{\text{unknown}}$)** | Static hypothesis in pool. | **Functional Open-Set Engine**: dynamically measures residual disorder, elevates $H_{\text{unknown}}$, refuses forced classification, and suggests hypothesis expansions. |
| **Auditability & Provenance** | Markdown & JSON summaries. | **Formal Decision Provenance Graph (DAG)** in Mermaid/JSON + **Cryptographic SHA-256 Event Chaining** + **Deterministic Replay Engine**. |
| **Explanations** | Descriptive text summary. | **Counterfactual Decision Boundary Analysis**: calculates exact minimal evidence changes required to flip decisions. |
| **Enterprise Isolation** | Single-case execution. | **Multi-Case Fleet Isolation** with tenant boundaries, optimistic locks, and lease version counters. |
| **Benchmarking** | Anomaly detection seeds. | **10-Family Investigation Benchmark** with **Privileged Oracle Regret** and **Quality-Cost Pareto Frontier**. |
| **Multimodality** | None. | **Sandboxed Multimodal Evidence Adapter**: cross-checks analyst charts/reports against deterministic series data. |

---

## 2. Backward Compatibility
- Existing API calls to `InvestigationEngine.investigate()` continue to function seamlessly.
- Command-line interfaces from v0.3 (`judge-demo`, `hero-demo`, `control-demo`, `real-demo`, `benchmark`, `schema`, `preregistration`) remain fully functional with enhanced telemetry.
