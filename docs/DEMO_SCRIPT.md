# ASTRA v0.3 — Video Demonstration Script (2–3 Minutes)

This script outlines the canonical 2–3 minute video presentation of ASTRA v0.3.

---

### Timeline Breakdown

| Timestamp | Section | Key Visual / Terminal Output | Voiceover Script |
|---|---|---|---|
| **0:00 – 0:25** | **The Problem** | Slide / Diagram showing alert fatigue from passive detectors | *"Traditional anomaly detectors act like smoke alarms: they flag when something unusual happens, but leave human analysts drowning in false positives without explaining why. ASTRA v0.3 changes this by transforming passive detection into autonomous, evidence-driven investigation."* |
| **0:25 – 0:50** | **The Architecture** | Architecture diagram showing State Machine, Hypotheses, DSL Sandbox | *"ASTRA operates under strict architectural discipline. An investigation state machine guides the lifecycle, maintaining five competing hypotheses. An AI or heuristic planner selects discriminative tests, but can only execute approved operations through a restricted, sandboxed DSL."* |
| **0:50 – 1:50** | **Live Terminal Execution (`astra judge-demo`)** | Live terminal running `python -m astra_poc judge-demo` | *"Let's watch a live investigation. An unusual signal is detected at t=720. ASTRA opens an investigation and posits five hypotheses. In Step 1, it deploys window contrast testing. In Step 2, it runs PELT exact partitioning. Notice what happens: the initial leading hypothesis—that this was just transient noise—is contradicted and falsified. ASTRA changes its mind, promotes regime change to leading status, and escalates with a full audit package—all in under 2 seconds."* |
| **1:50 – 2:20** | **Control Scenario & Safety Boundary** | Live terminal running `astra control-demo` & `astra demo-failures` | *"Now watch the control scenario. When presented with benign noise, ASTRA proves H1, avoiding false alarm escalation. And when subjected to adversarial code injection or budget exhaustion, the DSL validator blocks the attempt instantly."* |
| **2:20 – 2:45** | **Cloud Readiness & Benchmarks** | Cloud Run service & benchmark summary table | *"ASTRA is deployable to Google Cloud Run with one command, integrating with Gemini API while supporting full local reproduction. In 30-seed benchmarks with 95% Wilson confidence intervals, ASTRA demonstrates 100% recall with explicit falsification metrics."* |
| **2:45 – 3:00** | **Conclusion & Epistemic Honesty** | Limitations slide | *"ASTRA v0.3 remains an honest Proof of Concept: synthetic claims are kept strictly separate from real-world telemetry, with no fabricated guarantees. Thank you."* |
