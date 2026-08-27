# ASTRA v0.3 — Scientific Threats to Validity

---

## 1. Internal Validity
- **Shared Assumptions:** The synthetic generator and change-point detectors share Gaussian and variance-jump modeling assumptions.
- **Hyperparameter Sensitivity:** Preregistered baselines (CUSUM, Page-Hinkley, PELT, BOCPD) have differing sensitivities to threshold tuning.
- **Algorithmic Co-dependence:** Independent confirmation on the same single time series does not constitute a completely independent empirical data source.

**Mitigations:** Thresholds are preregistered and SHA-256 hashed; one-to-one temporal matching is strictly enforced; PELT baseline victories over ASTRA are published transparently rather than hidden.

---

## 2. External Validity
- **Synthetic Representativeness:** 30 seeds drawn from a controlled synthetic generator do not reflect the full complexity, microstructure, or regime diversity of live financial markets or distributed system telemetry.
- **Epistemic Isolation:** Performance metrics obtained on Track A (synthetic) must never be extrapolated to claim real-world production accuracy.

**Mitigations:** Track B (Real-World Benchmark) is maintained as an isolated evaluation track with explicit zero-ground-truth labeling discipline.

---

## 3. Construct Validity
- **Heuristic Evidence Score:** `evidence_score` is an operational heuristic ranking, not a calibrated Bayesian posterior probability.
- **Tolerance Windows:** Time-point matching tolerances (e.g., 3.5% of series length) do not have direct economic loss-function equivalence.
- **Stacking Association vs Causality:** Temporal null stacking measures statistical alignment under circular time-shift; it does not establish causal identification.

---

## 4. Conclusion Validity
- **Wilson Confidence Intervals:** Wilson 95% intervals quantify statistical uncertainty due to finite sample size within the generator; they do not quantify uncertainty about unobserved data distributions.
- **Multiple Testing:** Multiple hypothesis tests in the investigation loop are tracked and recorded in the audit trail.
