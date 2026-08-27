# ASTRA v0.4 — System Architecture & Decision Science Layer

---

## 1. Architectural Philosophy: Rational Investigation Control

ASTRA v0.4 evolves from executing an autonomous investigation workflow into **Rational Investigation Control and Decision Science**.

Key principles:
1. **Decision Science over Static Workflow**: Rather than stepping through a predetermined test sequence, ASTRA asks at each step: *"What is the expected value of acquiring more evidence, what is its cost and risk, and is it time to stop?"*
2. **Adaptive Utility Model**: Evaluates candidate actions via:
   $$U(a) = \alpha \cdot \text{EIG}(a) + \beta \cdot \text{EFG}(a) + \gamma \cdot \text{EDR}(a) - \lambda_c C(a) - \lambda_t T(a) - \lambda_r R(a)$$
3. **Value of Information (VoI) Stopping**: Formally computes $\text{VoI}(a)$. If acquiring new evidence costs more than its expected decision value ($\text{VoI} \le 0$), testing stops immediately.
4. **Functional $H_{\text{unknown}}$ & Open-Set Handling**: Unmodeled dynamics dynamically elevate $H_{\text{unknown}}$, allowing ASTRA to refuse forced classification into known hypotheses.
5. **Counterfactual & Provenance Auditability**: Produces formal Decision Provenance DAGs (Mermaid + JSON) and calculates exact counterfactual evidence boundaries.
6. **Fortified Multi-Case Fleet Isolation**: Independent concurrent cases with optimistic lease locks, version counters, and strict tenant boundaries.

---

## 2. Complete High-Level Architecture Diagram

```text
                  +-----------------------------------+
                  |   Event Stream / Ingestion Source |
                  |   (Track A Synthetic / Track B)   |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |         Signal & Regime Gate      |
                  |  (Robust Z-score / Preliminary)   |
                  +-----------------+-----------------+
                                    | Anomaly Trigger
                                    v
                  +-----------------------------------+
                  |    Investigation State Machine    |
                  |   (Formal Transition Enforcement) |
                  +-----------------+-----------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|    Hypothesis Pool    |                       |   Open-Set Dynamics   |
| (H1, H2, H3, H4, H_u) |                       |  (Residual Variance)  |
+-----------+-----------+                       +-----------+-----------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |      Decision Science Layer       |
                  |  (VoI / Utility / Recoverability) |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |      Formal Stopping Policy       |
                  | (Sufficiency / VoI <= 0 / Unknown)|
                  +--------+-----------------+--------+
                           | Continue        | Stop
                           v                 v
            +-----------------------+   +-----------------------+
            |     Restricted DSL    |   |    Decision Policy    |
            |     Schema Boundary   |   | (CLOSE/WATCH/ESCALATE)|
            +-----------+-----------+   +-----------+-----------+
                        |                           |
                        v                           v
            +-----------------------+   +-----------------------+
            |      DSL Sandbox      |   | Counterfactual Engine |
            | (Deterministic Exec)  |   |  & Provenance Graph   |
            +-----------+-----------+   +-----------+-----------+
                        | Results                   |
                        v                           v
            +-----------------------+   +-----------------------+
            | Falsification Engine  |   |  Tamper-Evident Chain |
            |  (Disprove & Update)  |   |  (SHA-256 Event Chain)|
            +-----------+-----------+   +-----------------------+
```

---

## 3. Investigation State Machine & Stopping Reasons

| State | Role | Valid Outbound Transitions |
|---|---|---|
| `OBSERVING` | Nominal event monitoring. | `SIGNAL_DETECTED` |
| `SIGNAL_DETECTED` | Anomaly peak flagged by Robust Z-score. | `TRIAGING` |
| `TRIAGING` | Fast initial triage scan. | `INVESTIGATING`, `CLOSED` |
| `INVESTIGATING` | Bounded diagnostic loop. | `DECISION_READY`, `EVIDENCE_INSUFFICIENT` |
| `DECISION_READY` | Sufficient evidence acquired. | `CLOSED`, `WATCHING`, `ESCALATED`, `HUMAN_REVIEW_REQUIRED` |
| `EVIDENCE_INSUFFICIENT`| Budget or information exhausted. | `WATCHING`, `ESCALATED`, `DEFERRED`, `HUMAN_REVIEW_REQUIRED` |
| `CLOSED` / `WATCHING` / `ESCALATED` / `DEFERRED` / `HUMAN_REVIEW_REQUIRED` | Terminal resolution states. | `None` (Immutable) |

---

## 4. Multi-Case Fleet Isolation & Concurrency Control

```text
               +----------------------------------+
               |      CaseIsolationManager        |
               +-----------------+----------------+
                                 |
         +-----------------------+-----------------------+
         |                                               |
         v                                               v
+------------------+                            +------------------+
| CaseContext A    |                            | CaseContext B    |
| - case_id: A101  |                            | - case_id: B202  |
| - tenant: alpha  |                            | - tenant: beta   |
| - budget: 10.0u  |                            | - budget: 5.0u   |
| - version: 2     |                            | - version: 1     |
| - lease: valid   |                            | - lease: valid   |
+------------------+                            +------------------+
```

Optimistic locking guarantees that two concurrent workers cannot mutate the same case without acquiring the latest lease token, preventing race conditions and cross-case state leakage.
