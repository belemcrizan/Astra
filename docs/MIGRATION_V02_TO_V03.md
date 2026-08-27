# ASTRA Migration Guide — v0.2 to v0.3

---

## 1. What Changed

| Dimension | ASTRA v0.2 | ASTRA v0.3 |
|---|---|---|
| **Operational Paradigm** | Passive detection and reporting. | **Evidence-driven autonomous investigation.** |
| **Lifecycle Model** | Linear DAG (`analytics` $\rightarrow$ `hypothesis` $\rightarrow$ `falsification` $\rightarrow$ `governance`). | **Formal State Machine** (`OBSERVING` $\rightarrow$ `SIGNAL_DETECTED` $\rightarrow$ `TRIAGING` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `DECISION_READY` $\rightarrow$ `CLOSED/WATCH/ESCALATE`). |
| **Hypotheses** | 2 static claims (H1, H2). | **5 Competing Hypotheses** ($H_1$ Noise, $H_2$ Regime, $H_3$ Break, $H_4$ Weak Signal, $H_{\text{unknown}}$). |
| **Evidence Collection** | Pre-determined static tests. | **Discriminative Evidence Selection** based on Information Value / Cost ratio ($E[I]/C$). |
| **Falsification** | Static Pelican/Stacking check. | **Active Falsification Engine** capable of disproving hypotheses and changing mind during investigation. |
| **Execution Safety** | Hardcoded Python execution. | **Restricted DSL Sandbox** with deterministic schema and bounds validation. |
| **Evaluation Tracks** | Track A (Synthetic only). | **Track A (Synthetic with ground truth) + Track B (Real-world telemetry without ground truth).** |
| **Language & Docs** | Mixed Portuguese/English. | **100% Technical English across code, CLI, logs, and docs.** |

---

## 2. Backward Compatibility
- Existing API calls to `OrchestratorAgent(settings).investigate()` continue to function seamlessly, returning an `InvestigationReport` populated with all legacy and v0.3 fields.
- Historical benchmark metrics (precision, recall, F1, Wilson 95% CIs, PELT, CUSUM, BOCPD) remain fully computed and verified.
