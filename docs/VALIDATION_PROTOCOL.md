# ASTRA v0.3 — Scientific Validation Protocol

---

## 1. Experimental Controls
1. **Hidden Ground Truth:** Ground truth labels are completely withheld from analytical agents and investigation planners; they are accessed solely by the evaluation module.
2. **One-to-One Dynamic Matching:** Predictions and true change-points are matched using an order-preserving dynamic program that maximizes true positives while minimizing absolute delay. Duplicate predictions within the tolerance window are penalized as false positives.
3. **95% Wilson Confidence Intervals:** Reported for precision, recall, and hypothesis significance rates to expose uncertainty on finite observation sets.
4. **H2 Zero-Signal Null Benchmark:** Evaluates empirical false positive rates of temporal null stacking by running on series with injected signal amplitude $= 0.0$.
5. **Preregistration Identity:** Methodological parameters and threshold definitions are frozen and canonicalized into a SHA-256 hash embedded in every output report.
6. **Ablation Protocol:** Systematically evaluates Full ASTRA against 3 ablation configurations (Fixed-Sequence, Falsification-Only, Detection-Only) to isolate component value.

---

## 2. Validation Commands
To replicate the full experimental validation locally:

```bash
# 1. Run full unit and regression test suite
python -m unittest discover -s tests -v

# 2. Run 30-seed scientific benchmark
python -m astra_poc benchmark --seeds 30

# 3. Run investigation ablations
python -m astra_poc ablations --seeds 15

# 4. Verify methodology hash and preregistration
python -m astra_poc preregistration

# 5. Validate JSON Schema integrity
python -m astra_poc schema
```
