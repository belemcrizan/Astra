# ASTRA v0.4 — Video Demonstration Script (2–3 Minutes)

This script outlines the canonical 2–3 minute video presentation of ASTRA v0.4.

---

### Timeline Breakdown

| Timestamp | Section | Key Visual / Terminal Output | Voiceover Script |
|---|---|---|---|
| **0:00 – 0:30** | **The Problem & Thesis** | Slide / Diagram showing alert fatigue and cost of unguided tests | *"Traditional anomaly detectors alert operators when something unusual happens, but leave them to guess why. ASTRA v0.4 moves beyond passive workflows to Rational Investigation Control: deciding what experiment is worth running next, weighing information gain against cost, and knowing when to stop."* |
| **0:30 – 1:00** | **Architecture & Decision Science** | Architecture diagram showing State Machine, VoI Utility Engine, and DSL Sandbox | *"ASTRA operates under rigorous decision science. It maintains five competing explanations, including unmodeled open-set dynamics. At each step, an adaptive utility engine ranks candidate diagnostic tests based on expected information gain, falsification power, and compute cost."* |
| **1:00 – 1:55** | **Live Terminal Execution (`astra judge-demo`)** | Live terminal running `python -m astra_poc judge-demo --explain-policy` | *"Let's watch a live investigation. At t=720, an anomaly is detected. In Step 1, ASTRA evaluates all candidate operations and ranks their Value of Information. It deploys entropy calculation and sub-window contrast. Notice what happens: initial belief H1—that this was just noise—is contradicted and falsified. When further testing provides non-positive VoI, ASTRA stops immediately and escalates with a full counterfactual analysis and tamper-evident SHA-256 integrity chain—all in 1.5 seconds."* |
| **1:55 – 2:25** | **Open-Set ($H_{\text{unknown}}$) & Pareto Frontier** | Terminal running `astra unknown-demo` and `astra pareto-frontier` | *"When presented with chaotic, unmodeled data in Family H, ASTRA refuses forced classification, elevating H_unknown and safely deferring to human operators. In benchmark evaluations across scenario families, ASTRA's adaptive policy achieves Pareto dominance over static and naive baselines."* |
| **2:25 – 2:45** | **Fleet Multi-Case Isolation & Replay** | Terminal running `astra replay <report>` and `astra verify-report <report>` | *"For enterprise deployment, ASTRA enforces strict case isolation with optimistic locking and provides deterministic investigation replay with cryptographic verification."* |
| **2:45 – 3:00** | **Conclusion & Epistemic Honesty** | Limitations slide | *"ASTRA v0.4 remains an honest, reproducible research Proof of Concept. Controlled synthetic benchmarks are kept strictly separate from empirical real-world series. Thank you."* |
