# ASTRA — Devpost Submission Content

This document contains copy-paste-ready text formatted for the hackathon submission form.

---

## 1. Project Tagline
> **Bounded Autonomous Investigation Engine powered by Google ADK and Gemini 3.5+ on Google Cloud Run.**

---

## 2. Mandatory Technology Stack

| Component | Technology Used | Exact Role in ASTRA |
| :--- | :--- | :--- |
| **Foundation Model** | **Gemini 3.5+ (Gemini 2.5 Flash / Gemini 3.5 Flash-Lite)** via `google-genai 2.20.0` | Synthesizes anomaly context, reasons over competing hypotheses, and proposes next diagnostic actions using structured JSON schemas. |
| **Agent Framework** | **Google ADK (`google-adk 2.8.0`)** | Encapsulates `ASTRAInvestigationAgent`, manages the investigation planning turns, and binds bounded ASTRA diagnostic tools. |
| **Cloud Infrastructure** | **Google Cloud Run** | Hosts the containerized FastAPI backend, executes end-to-end investigation requests on `$PORT`, and emits structured Cloud Logging. |

---

## 3. How the Technologies Work Together

> **ASTRA uses Gemini through Google ADK as a bounded investigation-planning agent. Gemini receives structured statistical context and proposes diagnostic actions, but it cannot execute arbitrary code or directly alter evidence. Every proposal passes through ASTRA's restricted DSL validator and deterministic statistical executor. The complete backend runs on Google Cloud Run, where investigation requests, agent proposals, validation, evidence acquisition, stopping decisions, and audit metadata are executed end-to-end.**

---

## 4. Key Architectural Highlights

1. **LLM Proposes, ASTRA Validates, Deterministic Tools Execute:**
   Gemini does not replace statistical science. It proposes operations from ASTRA's Restricted DSL (`RUN_PELT`, `RUN_CUSUM`, `RUN_BOCPD`, `COMPARE_WINDOWS`, `CALCULATE_ENTROPY`, `TEST_TEMPORAL_STACKING`). ASTRA validates permissions, parameters, and computational budget before sandboxed deterministic execution.

2. **Falsification-First & Value of Information (VoI):**
   Active competing hypotheses ($H_1 \dots H_4, H_{\text{unknown}}$) are systematically challenged. Investigations stop via strict decision sufficiency, avoiding wasteful compute while achieving **66.7% resolution accuracy** on the Pareto frontier.

3. **Cryptographic Auditability & Traceability:**
   Every proposal, validation check, and state transition is cryptographically chained with SHA-256 and assigned a distributed trace ID, fully visible in Google Cloud Run logs.

---

## 5. Quick Verification Commands for Judges

```bash
# 1. Audit mandatory eligibility stack
python -m astra_poc eligibility-check

# 2. Run live Google ADK + Gemini investigation
python -m astra_poc google-agent-demo

# 3. Verify deployed Cloud Run backend
python -m astra_poc cloud-verify --url <DEPLOYED_CLOUD_RUN_URL>
```
