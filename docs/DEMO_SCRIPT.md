# ASTRA — Hackathon Video Demonstration Script (3:30 Target)

This script outlines the exact timing, narration, and screen actions for the required public demo video.

---

## Video Timeline & Stage Directions

### 0:00 – 0:25 | The Core Problem
- **Screen:** Typical monitoring dashboard with an uninformative anomaly alert spike.
- **Narration (English):**
  > "Modern anomaly detectors tell teams that something unusual happened. But they do not decide what evidence is worth acquiring next, which hypothesis should be falsified, or when an investigation should safely stop. Teams are either flooded with false alarms or forced to perform manual, costly diagnostic forensics."

---

### 0:25 – 0:45 | Introducing ASTRA
- **Screen:** ASTRA GitHub repository and terminal header.
- **Narration:**
  > "ASTRA is a bounded autonomous investigation engine for weak signals and regime shifts. It uses Google ADK and Gemini 3.5+ for investigation planning, while enforcing a strict deterministic execution boundary that validates every proposed action before running it."

---

### 0:45 – 1:05 | Google Stack Architecture
- **Screen:** Architecture Diagram (`docs/GOOGLE_AGENT_ARCHITECTURE.md`).
- **Narration:**
  > "Here is how our Google stack works end-to-end:
  > The backend is deployed on Google Cloud Run. When an anomaly triggers, the Google ADK Agent queries Gemini with structured context. Gemini proposes the next best diagnostic experiment. ASTRA's Restricted DSL Validator inspects the proposal for safety, parameter bounds, and budget. Only then does our sandboxed statistical kernel execute the test, update competing hypotheses, and trigger our Value-of-Information stopping policy."

---

### 1:05 – 2:30 | Live Execution Demo
- **Screen:** Terminal running `python -m astra_poc google-agent-demo`.
- **Narration:**
  > "Let's watch a live investigation turn-by-turn.
  > Notice the stack: Google ADK, Gemini 2.5 Flash, and ASTRA Restricted DSL.
  > When an anomaly occurs at t=600, ASTRA initializes four competing hypotheses plus H_unknown.
  > In Turn 1, Gemini proposes `COMPARE_WINDOWS` to contrast variance regimes. ASTRA's DSL validator approves it. The sandboxed executor detects a significant shift, contradicting the transient noise hypothesis H1.
  > In Turn 2, Gemini proposes `RUN_PELT` segmentation, confirming an abrupt break.
  > ASTRA's stopping policy recognizes Decision Sufficiency and halts the investigation, returning ESCALATE with a 77.5% reliability score and full reason codes."

---

### 2:30 – 2:55 | Auditability & Governance
- **Screen:** JSON audit report and counterfactual explanations.
- **Narration:**
  > "Every single step is cryptographically hashed with SHA-256 in an integrity chain. ASTRA also produces exact counterfactual explanations—explaining precisely what evidence delta would have been required to reach an alternative decision like CLOSE or DEFER."

---

### 2:55 – 3:20 | Google Cloud Run Live Verification (CRITICAL)
- **Screen:** Google Cloud Console showing Cloud Run Service `astra-poc`, active revision, and live Cloud Logging stream.
- **Action:** Open terminal and run:
  ```bash
  curl -X GET https://astra-poc-XXXX-uc.a.run.app/health
  curl -X POST https://astra-poc-XXXX-uc.a.run.app/agent/investigate -H "Content-Type: application/json" -d '{"scenario": "hero", "seed": 42}'
  ```
- **Narration:**
  > "Here is the live Google Cloud Run console showing our active revision and real-time structured logs. Invoking the `/health` and `/agent/investigate` endpoints on Cloud Run executes the Google ADK agent and ASTRA kernel remotely in under 300 milliseconds, returning verified runtime metadata and distributed trace IDs."

---

### 3:20 – 3:35 | Conclusion
- **Screen:** ASTRA Title Slide with GitHub URL and Google Stack Badges (Gemini, Google ADK, Cloud Run).
- **Narration:**
  > "Gemini proposes. ASTRA verifies. Google Cloud runs the investigation. ASTRA proves that autonomous AI agents can be made scientifically rigorous, bounded, and audit-ready."
