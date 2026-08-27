# ASTRA v0.4.1 — Autonomous Evidence-Driven Investigation Engine

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

| Traditional Anomaly Detector | Unconstrained AI Agent | ASTRA v0.4.1 |
|---|---|---|
| Binary alerts (*"Anomaly at t=720"*). | Generates unverified code with arbitrary execution risks. | **Bounded Rational Investigation**: Evaluates Value of Information before running diagnostic tests. |
| Zero hypothesis modeling. | Hallucinates confidence scores without falsification. | **Competing Hypotheses & Falsification-First**: Deliberately attempts to disprove candidate explanations. |
| Static alert rules causing alert fatigue. | Unbounded looping and unpredictable API costs. | **Formal Stopping Policy**: Halts immediately when $\text{VoI} \le 0$, sufficiency is reached, or unmodeled regimes dominate. |
| No explanation of what would change the alert. | Black-box unexplainable output. | **Counterfactual Decision Boundaries**: Explains exact minimal evidence changes to alter decisions. |
| No cryptographic audit trail. | Ephemeral text chats without replayability. | **Tamper-Evident SHA-256 Chains & Deterministic Replay Engine**. |

---

## 4. Quick Start

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

# 8. Run Track B real-world empirical evaluation
python -m astra_poc real-demo

# 9. Compute Quality-Cost Pareto Frontier across investigation policies
python -m astra_poc pareto-frontier

# 10. Run 30-seed scientific investigation benchmark
python -m astra_poc benchmark --seeds 30

# 11. Run full automated test suite (65 tests)
python -m unittest discover -s tests -v
```

---

## 5. Experimental Results & Quality-Cost Pareto Frontier

### Quality–Cost Pareto Frontier (15 Seeds per Policy across Benchmark Scenario Families)

| Investigation Policy | Resolution Accuracy | Mean Cost | P95 Latency | Pareto Efficient |
|---|---:|---:|---:|:---:|
| **Fixed-Sequence Baseline** | 46.7% | 1.20u | 228.7 ms | **YES (Low Cost Boundary)** |
| **ASTRA Full (Adaptive VoI)** | **66.7%** | **1.80u** | **208.8 ms** | **YES (Dominates Accuracy)** |
| **Falsification-Only** | 66.7% | 2.27u | 331.8 ms | No (Dominated by ASTRA) |

*Finding: ASTRA's adaptive VoI policy matches the peak 66.7% resolution accuracy of unconstrained falsification while saving **20.7% compute cost** and reducing P95 latency from 331.8 ms to 208.8 ms.*

---

## 6. Documentation Index

- [Corrective Validation & Root Cause Analysis](docs/V04_1_CORRECTIVE_VALIDATION.md)
- [Negative Results & Disproven Architectures](docs/NEGATIVE_RESULTS.md)
- [Claims & Evidence Alignment Matrix](docs/CLAIMS_AND_EVIDENCE.md)
- [Architecture & Decision Science Layer](docs/ARCHITECTURE_V04.md)
- [Non-Technical Guide](docs/NON_TECHNICAL_GUIDE.md)
- [Judging Evidence Matrix](docs/JUDGING_EVIDENCE.md)
- [Video Demo Script](docs/DEMO_SCRIPT.md)
- [Dataset Cards (Track A & B + 10 Families)](docs/DATASET_CARD.md)
- [STRIDE Threat Model](docs/THREAT_MODEL_STRIDE.md)
- [Threats to Validity](docs/THREATS_TO_VALIDITY.md)
- [Scientific Validation Protocol](docs/VALIDATION_PROTOCOL.md)
- [Preregistration Identity](PREREGISTRATION.md)
- [Google Cloud Deployment Guide](deploy/README.md)

---

## 7. Fortified Multi-Case Fleet Isolation

For enterprise deployment, ASTRA provides isolated investigation boundaries:
- **Tenant & Case Isolation**: `CaseIsolationManager` guards against cross-tenant or cross-case data leakage.
- **Optimistic Leases**: Prevents concurrent stale state mutations via optimistic locking version counters.
- **Tamper-Evident Chaining**: Every lifecycle event is cryptographically hashed with SHA-256.

---

## 8. Google Cloud Run Deployment

ASTRA is containerized and ready for **Google Cloud Run**:

```bash
# One-command deployment
./deploy/deploy_cloud_run.sh YOUR_PROJECT_ID us-central1
```

See [`deploy/README.md`](deploy/README.md) for full deployment instructions, Secret Manager integration, and health check verification.

---

## 9. Limitations & Epistemic Honesty

1. **Synthetic vs Real**: Synthetic benchmark results establish statistical sanity under controlled generative assumptions, not external real-world accuracy.
2. **Heuristic Scoring**: `evidence_score` is an operational ranking metric, not a calibrated probability.
3. **Bounded Scope**: ASTRA is a research POC. It provides decision support and audit trails; it does not replace human domain expertise or execute production interventions.
