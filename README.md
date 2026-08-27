# ASTRA v0.4 — Autonomous Evidence-Driven Investigation Engine

> **ASTRA** turns anomaly alerts into bounded, evidence-backed investigations. Instead of escalating every unusual signal or guessing blindly, ASTRA maintains competing explanations, chooses the next diagnostic experiment based on expected decision utility, attempts to falsify its own hypotheses, recognizes when none of its known models fit, and stops when additional information is no longer worth its cost.

[![CI](https://github.com/belemcrizan/Astra/actions/workflows/ci.yml/badge.svg)](https://github.com/belemcrizan/Astra/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Cloud%20Run%20Ready-blue.svg)](deploy/README.md)

---

## 1. Why ASTRA Exists

Traditional anomaly detectors behave like simple smoke alarms: they alert you when an unusual measurement occurs, but cannot explain **why** it happened or distinguish between benign noise, structural shifts, and subtle coordinated patterns. As a result, operations teams face crippling **alert fatigue**, drowning in uncontextualized false alarms.

ASTRA evolves anomaly detection from **passive alerting** to **Rational Investigation Control**:
When an unusual signal is detected, ASTRA opens an investigation case, maintains competing hypotheses, calculates the **Value of Information (VoI)** for candidate tests, executes targeted diagnostic experiments in a restricted sandbox to attempt to **disprove** candidate explanations, and produces an auditable decision package (`CLOSE`, `WATCH`, `DEFER`, or `ESCALATE`).

> [!IMPORTANT]
> **Proof of Concept Status**: ASTRA is a research Proof of Concept (POC). It is not certified for live trading, automated financial orders, or AML enforcement. No automated external interventions are authorized.

---

## 2. 60-Second Overview

```text
Observed Event Stream
        |
        v
Signal & Regime Gate (Robust Z-score | MAD)
        |
   +----+----+
   |         |
Nominal   Suspicious Anomaly
   |         |
   |         v
   |   Investigation Case Opened (Isolated Fleet Context)
   |         |
   |         v
   |   Competing Hypotheses + Functional H_unknown
   |   (H1: Noise, H2: Regime, H3: Break, H4: Signal, H_unknown)
   |         |
   |         v
   |   Value of Information (VoI) Utility Ranking
   |   U(a) = α·EIG + β·EFG + γ·EDR - λ_c·C - λ_t·T - λ_r·R
   |         |
   |         v
   |   Restricted DSL Sandbox Execution
   |         |
   |         v
   |   Falsification & Belief Update (Changing Mind upon Falsification)
   |         |
   |         v
   |   Formal Stopping Policy (VoI <= 0 / Decision Sufficient / Unknown)
   |    /    |      |     \
   | CLOSE  WATCH  DEFER  ESCALATE
   |                |       |
   |                +---+---+
   |                    |
   |                    v
   |           Human Review Package & Counterfactuals
   |                    |
   +--------------------+
            |
            v
   Decision Provenance Graph (DAG) & SHA-256 Tamper-Evident Chain
```

---

## 3. What Makes ASTRA Different

| Traditional Anomaly Detector | Unconstrained AI Agent | ASTRA v0.4 |
|---|---|---|
| Binary alerts (*"Anomaly at t=720"*). | Generates unverified code with arbitrary execution risks. | **Bounded Rational Investigation**: Evaluates Value of Information before running diagnostic tests. |
| Zero hypothesis modeling. | Hallucinates confidence scores without falsification. | **Competing Hypotheses & Falsification-First**: Deliberately attempts to disprove candidate explanations. |
| Static alert rules causing alert fatigue. | Unbounded looping and unpredictable API costs. | **Formal Stopping Policy**: Halts immediately when $\text{VoI} \le 0$ or uncertainty is resolved. |
| No explanation of what would change the alert. | Black-box unexplainable output. | **Counterfactual Decision Boundaries**: Explains exact minimal evidence changes to alter decisions. |
| No cryptographic audit trail. | Ephemeral text chats without replayability. | **Tamper-Evident SHA-256 Chains & Deterministic Replay Engine**. |

---

## 4. Architecture & Decision Science Layer

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

## 5. Core Decision Science Capabilities

### A. Adaptive Utility Model & Value of Information (VoI)
At every step $t$, ASTRA evaluates candidate diagnostic tests $a \in A_t$ by computing:
$$U(a) = \alpha \cdot \text{EIG}(a) + \beta \cdot \text{EFG}(a) + \gamma \cdot \text{EDR}(a) - \lambda_c C(a) - \lambda_t T(a) - \lambda_r R(a)$$
where:
- $\text{EIG}(a)$: **Expected Information Gain** (discrimination power across top hypothesis pair).
- $\text{EFG}(a)$: **Expected Falsification Gain** (utility of disproving the leading plausible hypothesis).
- $\text{EDR}(a)$: **Expected Decision Relevance** (divergence between actions implied by competing hypotheses).
- $C(a)$, $T(a)$, $R(a)$: Computational cost, latency, and operational recoverability penalty.

### B. Functional Open-Set Recognition ($H_{\text{unknown}}$)
When incoming data exhibits heavy-tailed or non-parametric dynamics that contradict all known models ($H_1 \dots H_4$), $H_{\text{unknown}}$ score is dynamically elevated. ASTRA **refuses forced classification**, halting the investigation with `DEFER` and proposing hypothesis expansions.

### C. Counterfactual Decision Boundaries
Every decision includes exact counterfactual boundary statements:
> *"If sub-window contrast had exceeded 0.75, decision would flip from `CLOSE` to `ESCALATE`."*
> *"If $H_{\text{unknown}}$ exceeded 0.60, decision would flip to `DEFER`."*

### D. Decision Provenance Graph (DAG) & Deterministic Replay
Investigations construct a complete DAG connecting observations $\rightarrow$ hypotheses $\rightarrow$ candidate utility rankings $\rightarrow$ executed tests $\rightarrow$ evidence items $\rightarrow$ decisions. Reports embed cryptographic SHA-256 hash chains ($H_t = \text{SHA256}(H_{t-1} \parallel \text{event}_t)$) and can be deterministically replayed and verified.

---

## 6. Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/belemcrizan/Astra.git
cd Astra

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

### Essential Commands

```bash
# 1. Run live hackathon judge demonstration (<2 seconds)
python -m astra_poc judge-demo --explain-policy

# 2. Run hero scenario (hypothesis trap, falsification, and change of mind)
python -m astra_poc hero-demo

# 3. Run control scenario (benign noise safe closure with VoI <= 0 stop)
python -m astra_poc control-demo

# 4. Run open-set unknown regime demo (refusing forced classification)
python -m astra_poc unknown-demo

# 5. Run budget adaptation demo (Low vs Med vs High budget comparison)
python -m astra_poc budget-demo

# 6. Run adversarial stress & fault injection demo
python -m astra_poc adversarial-demo

# 7. Run sandboxed multimodal evidence cross-check demo
python -m astra_poc multimodal-demo

# 8. Compute Quality-Cost Pareto Frontier across investigation policies
python -m astra_poc pareto-frontier

# 9. Verify cryptographic integrity of a report artifact
python -m astra_poc verify-report artifacts/reports/<run_id>.json

# 10. Deterministically replay an investigation
python -m astra_poc replay artifacts/reports/<run_id>.json

# 11. Run 30-seed scientific investigation benchmark
python -m astra_poc benchmark --seeds 30

# 12. Run full automated test suite (58 tests)
python -m unittest discover -s tests -v
```

---

## 7. Experimental Results & Quality-Cost Pareto Frontier

### Quality–Cost Pareto Frontier (15 Seeds per Policy across 5 Scenario Families)

| Investigation Policy | Correct Resolution | Mean Cost | P95 Latency | Pareto Efficient |
|---|---:|---:|---:|:---:|
| **ASTRA Full (Adaptive VoI)** | **26.7%** | **2.97u** | **512.7 ms** | **YES (Dominates)** |
| **Falsification-Only** | 26.7% | 4.37u | 670.4 ms | No (Dominated by ASTRA) |
| **Fixed-Sequence (No Adaptation)** | 20.0% | 5.00u | 660.3 ms | No (Dominated by ASTRA) |

*Finding: ASTRA's adaptive VoI policy achieves equal or superior accuracy with **40.6% lower compute cost** than fixed-sequence baselines.*

---

## 8. Fortified Multi-Case Fleet Isolation

For enterprise deployment, ASTRA provides isolated investigation boundaries:
- **Tenant & Case Isolation**: `CaseIsolationManager` guards against cross-tenant or cross-case data leakage.
- **Optimistic Leases**: Prevents concurrent stale state mutations via optimistic locking version counters.
- **Tamper-Evident Chaining**: Every lifecycle event is cryptographically hashed with SHA-256.

---

## 9. Google Cloud Run Deployment

ASTRA is containerized and ready for **Google Cloud Run**:

```bash
# One-command deployment
./deploy/deploy_cloud_run.sh YOUR_PROJECT_ID us-central1
```

See [`deploy/README.md`](deploy/README.md) for full deployment instructions, Secret Manager integration, and health check verification.

---

## 10. Documentation Index

- [Architecture & Decision Science Layer](docs/ARCHITECTURE_V04.md)
- [Non-Technical Guide](docs/NON_TECHNICAL_GUIDE.md)
- [Judging Evidence Matrix](docs/JUDGING_EVIDENCE.md)
- [Video Demo Script](docs/DEMO_SCRIPT.md)
- [Dataset Cards (Track A & B + 10 Families)](docs/DATASET_CARD.md)
- [STRIDE Threat Model](docs/THREAT_MODEL_STRIDE.md)
- [Threats to Validity](docs/THREATS_TO_VALIDITY.md)
- [Scientific Validation Protocol](docs/VALIDATION_PROTOCOL.md)
- [Agents & Statistical Methods](docs/AGENTS_AND_METHODS.md)
- [Migration Guide v0.3 $\rightarrow$ v0.4](docs/MIGRATION_V03_TO_V04.md)
- [Preregistration Identity](PREREGISTRATION.md)
- [Google Cloud Deployment Guide](deploy/README.md)

---

## 11. Limitations & Epistemic Honesty

1. **Synthetic vs Real**: Synthetic benchmark results establish statistical sanity under controlled generative assumptions, not external real-world accuracy.
2. **Heuristic Scoring**: `evidence_score` is an operational ranking metric, not a calibrated probability.
3. **Bounded Scope**: ASTRA is a research POC. It provides decision support and audit trails; it does not replace human domain expertise or execute production interventions.
