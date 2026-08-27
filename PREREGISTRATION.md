# Methodological Preregistration — ASTRA v0.4.1

This document formalizes the scientific experimental rules, decision science parameters, stopping policy precedence hierarchy, and detection thresholds for ASTRA v0.4.1 prior to benchmark execution. The executable definition is maintained in `src/astra_poc/preregistration.py`, and every generated report embeds the canonical SHA-256 hash of this configuration.

**Canonical Methodology SHA-256:** `1b2eeaeb0a3f842cb4afaab755bd27fee469b818e05298bdbfd64d73ac0975a4`

---

## 1. Primary Hypotheses & Open-Set Representation

- **H1 (Transient Statistical Fluctuation):** The observed anomaly is an isolated random noise outlier with no structural or volatility change.
- **H2 (Gradual Regime Change):** The series exhibits a persistent transition in mean return or variance clustering.
- **H3 (Abrupt Structural Break):** A sharp, discrete change-point occurred in the underlying distribution parameters.
- **H4 (Coordinated Weak Signal):** Events precede a structured, repeated weak response waveform detectable via temporal alignment.
- **H_unknown (Unmodeled Exogenous Dynamics):** Non-parametric or heavy-tailed dynamics outside standard Gaussian/autoregressive models.

---

## 2. Decision Science & Utility Parameters

- **Adaptive Utility Function:**
  $$U(a) = \alpha \cdot \text{EIG}(a) + \beta \cdot \text{EFG}(a) + \gamma \cdot \text{EDR}(a) - \lambda_c C(a) - \lambda_r R(a)$$
  with preregistered weights: $\alpha = 1.2$, $\beta = 1.5$, $\gamma = 1.0$, $\lambda_c = 0.35$, $\lambda_r = 0.20$.
- **Stopping Policy Precedence Hierarchy:**
  1. Safety / Governance Boundary
  2. Unknown Dominant ($H_{\text{unknown}} \ge 0.60$ or known models falsified)
  3. Decision Sufficiency ($\ge 65\%$ support with $\ge 20\%$ margin, or $H_1$ survived with alternatives ruled out)
  4. Information Exhausted (no unexecuted DSL operations remaining)
  5. Expected VoI Non-Positive ($\text{VoI} \le 0.05$ after $\ge 1$ test)
  6. Hypotheses Indistinguishable (tied active hypotheses with no further separating tests)
  7. Resource / Budget Exhausted (budget blocks execution of an otherwise positive-VoI action)
- **Value of Information (VoI) Threshold:** $0.05$ (testing stops when $\text{VoI} \le 0.05$ after minimum 1 test).
- **Open-Set Threshold:** $0.60$ (refuses forced classification when $H_{\text{unknown}} \ge 0.60$).
- **Selective Autonomy Threshold ($\tau$):** $0.65$ (defers to human review if decision reliability $< 0.65$).
- **Consequence Cost Assumptions:** False Close $= 10.0$, False Watch $= 3.0$, Unnecessary Escalate $= 2.0$, Unnecessary Defer $= 1.5$.
- **Investigation Budget Limits:** Maximum 5 steps, maximum 6 tests, maximum 10.0 cost units.

---

## 3. Epistemic Invariants

- No thresholds may be modified after observing benchmark outcomes without incrementing the methodology version and regenerating the SHA-256 identity.
- Synthetic controlled claims (Track A) and real-world empirical observations (Track B) must never be merged into aggregate metrics.
- `evidence_score` and `decision_reliability_score` are operational heuristic rankings, not calibrated Bayesian posterior probabilities.
