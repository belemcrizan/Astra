# Understanding ASTRA v0.3 — Non-Technical Guide

---

## 1. The Smoke Detector Analogy

Think of traditional anomaly detection like a household smoke detector:
- When a smoke detector beeps, it only tells you: *"Something unusual is in the air."*
- It cannot tell you whether the smoke came from burnt toast, steam from a hot shower, or an actual house fire.
- If the detector triggered an automatic fire truck response for every beep, the fire department would be overwhelmed with false alarms.

**ASTRA is not just a smoke detector.** 

When ASTRA detects an unusual event, it acts as an **autonomous investigator**:
1. It opens an investigation case file.
2. It considers several competing explanations (*"Is this routine kitchen steam, an electrical short-circuit, or a real fire?"*).
3. It selectively performs tests designed to **disprove** candidate explanations (*"If this were steam, humidity would be high and CO2 would be zero"*).
4. Based on the evidence, it updates its confidence and decides whether to **Close the alert**, **Watch the situation**, or **Escalate to a human operator**.

---

## 2. Why Competing Hypotheses Matter

Most automated systems jump directly from an anomaly to an assumption. ASTRA explicitly maintains multiple competing theories:
- **H1 (Transient Fluctuation)**: *"Just random noise; nothing fundamental changed."*
- **H2 (Gradual Regime Change)**: *"The system slowly shifted into a higher-volatility state."*
- **H3 (Abrupt Structural Break)**: *"A sharp, sudden shock occurred at this specific moment."*
- **H4 (Coordinated Weak Signal)**: *"A subtle, repeated pattern preceded the movement."*
- **H_unknown**: *"An external factor not modeled by standard rules."*

By forcing these hypotheses to compete against each other, ASTRA prevents confirmation bias.

---

## 3. Why Falsification Matters

In science, you do not prove a theory by looking only for things that support it; you test it by trying to disprove it.

ASTRA adopts a **falsification-first** philosophy:
- When a signal appears, the first hypothesis is often *"this is just noise"* ($H_1$).
- ASTRA immediately asks: *"What test would prove this is NOT just noise?"*
- If the test proves there is a real structural shift, ASTRA **rejects $H_1$ and changes its mind**.
- If the test shows nothing structural, $H_1$ survives, and the alert is **Closed without human intervention**, preventing alert fatigue.

---

## 4. What Are the Resource Bounds?

Autonomous systems must never run infinitely or burn unlimited computing power. ASTRA enforces hard mathematical budgets:
- Maximum 5 investigation steps per case.
- Maximum 6 diagnostic tests.
- Maximum 10 cost units of computation.

If the budget runs out while evidence remains ambiguous, ASTRA stops and flags the event as `DEFER` or `REQUEST_HUMAN_REVIEW`, explaining exactly what was tested and what remains uncertain.

---

## 5. What ASTRA Is (and Is Not)

| ASTRA Is | ASTRA Is Not |
|---|---|
| A research **Proof of Concept (POC)** demonstrating evidence-driven investigation. | A production-ready commercial platform. |
| A disciplined scientific kernel with 95% Wilson confidence intervals. | A certified anti-money-laundering (AML) compliance tool. |
| A safe sandbox where AI models can only request approved statistical tests. | An unconstrained autonomous bot that executes financial trades or external actions. |
| A system that strictly separates controlled synthetic benchmarks from real data. | A marketing claim of 100% real-world accuracy. |
