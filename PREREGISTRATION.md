# Methodological Preregistration — ASTRA v0.3

This document formalizes the scientific experimental rules and detection thresholds prior to benchmark evaluation. The executable definition is maintained in `src/astra_poc/preregistration.py`, and every generated report embeds the canonical SHA-256 hash of this configuration.

---

## 1. Primary Hypotheses

- **H1 (Transient Statistical Fluctuation):** The observed anomaly is a transient sampling outlier with no structural or volatility change.
- **H2 (Gradual Regime Change):** The series exhibits a persistent transition in mean return or volatility structure.
- **H3 (Abrupt Structural Break):** A sharp, discrete change-point occurred in the underlying distribution parameters.
- **H4 (Coordinated Weak Signal):** Events precede a structured, repeated weak response waveform detectable via temporal alignment.
- **H_unknown (Unmodeled Anomaly):** Residual dynamics not adequately modeled by existing parametric representations.

---

## 2. Frozen Evaluation Parameters

- **Change-point Matching:** One-to-one order-preserving matching via dynamic programming (`one_to_one_minimum_absolute_delay`).
- **Temporal Tolerance Window:** 3.5% of series length with a minimum threshold of 20 points.
- **Anomaly Detection Tolerance:** 2 discrete time steps.
- **Proportion Intervals:** Exact Wilson 95% confidence intervals.
- **Signal Detection Gate:** Robust Z-score $|z| \ge 7.0$ using median absolute deviation scaling ($1.4826 \times \text{MAD}$).
- **Regime Score Threshold:** Window size 100, score threshold 0.75, minimum separation 240 points.
- **Temporal Null Stacking (H4):** 999 circular time-shift permutations, one-sided upper tail, $\alpha = 0.01$.
- **Detection Baselines:** CUSUM, Page-Hinkley, Gaussian PELT, and BOCPD with frozen parameters.
- **Investigation Budget Limits:** Maximum 5 steps, maximum 6 tests, maximum 10.0 cost units.

---

## 3. Epistemic Invariants

- No thresholds may be modified after observing benchmark outcomes without incrementing the methodology version and regenerating the SHA-256 identity.
- Synthetic controlled claims (Track A) and real-world empirical observations (Track B) must never be merged into aggregate metrics.
- `evidence_score` is an operational heuristic ranking, not a calibrated probability.
