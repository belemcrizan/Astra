# Transparent Negative Results & Disproven Architectures

In keeping with scientific integrity, ASTRA documents both successful mechanisms and architectures that failed under rigorous empirical evaluation.

---

## 1. Unconstrained LLM Decision Generation (Ablated)
- **Concept:** Allowing a Large Language Model (LLM) to directly generate unstructured investigation plans and final decisions without a formal state machine or restricted DSL.
- **Observed Failure:** The LLM consistently exhibited confirmation bias—it generated justifications for the initial trigger anomaly regardless of counterevidence, frequently hallucinated test outputs that were never computed, and failed to respect computational budgets.
- **Architectural Resolution:** Replaced unconstrained LLM generation with the sandboxed DSL execution engine and formal state machine. The LLM is restricted to a structured planner role producing strictly validated DSL syntax.

---

## 2. Naive Cost-Penalized VoI without Multi-Hypothesis Normalization
- **Concept:** Penalizing candidate actions by $C(a) / \text{count}(\text{discriminated hypotheses})$.
- **Observed Failure:** Penalizing tests by the size of their candidate set caused the VoI engine to prioritize cheap, single-hypothesis, uninformative tests (e.g. partition entropy) over decisive segmentation algorithms (PELT, BOCPD). The investigation frequently consumed its entire budget on weak tests without ever resolving the true regime break.
- **Architectural Resolution:** Formulated EIG based on top-2 competitor overlap ($\min(1.0, \text{overlap}/2)$) and weighted Expected Falsification Gain (EFG) to prioritize tests that directly challenge the leading hypothesis.

---

## 3. Static Fixed-Sequence Policy Brittle Under Noise
- **Concept:** Executing a fixed pipeline of tests (`COMPARE_WINDOWS` -> `RUN_PELT` -> `RUN_CUSUM`) on every anomaly.
- **Observed Failure:** In Family A (Transient Noise) and Family H (Open-Set Heavy Tails), the fixed sequence executed unnecessary expensive segmentation algorithms even after the anomaly had already been decisively classified, incurring 1.20u cost on trivial events and achieving only 46.7% accuracy across diverse scenario families.
- **Architectural Resolution:** Adaptive evidence-driven policy dynamically terminates early via `DECISION_SUFFICIENT` or `UNKNOWN_DOMINANT`, achieving 66.7% accuracy with lower regret.

---

## 4. Single-Threshold Signal Gating
- **Concept:** Triggering investigations based purely on a standard Z-score threshold ($Z \ge 3.0$).
- **Observed Failure:** Standard sample variance is severely distorted by single isolated outliers (masking effect), causing the gate to miss subtle variance cluster transitions while triggering false alarms on nominal fat-tailed sampling noise.
- **Architectural Resolution:** Deployed median-based Robust Z-score ($Z_{\text{robust}} = \frac{x_t - \text{median}}{\text{MAD} \times 1.4826}$) with temporal stacking verification.
