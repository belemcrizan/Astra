# ASTRA v0.4 — Benchmark Summary Report

---

## 1. Primary Experimental Hypothesis
> An adaptive, evidence-driven investigation policy can reach high-quality investigation decisions with lower evidence cost, fewer unnecessary tests, and better uncertainty handling than fixed or naive investigation policies.

---

## 2. Quality-Cost Pareto Frontier

| Policy | Accuracy | Mean Cost | P95 Latency | Pareto Efficient |
|---|---:|---:|---:|:---:|
| **ASTRA Full (Adaptive VoI)** | **26.7%** | **2.97u** | **512.7 ms** | **YES (Dominates)** |
| **Falsification-Only** | 26.7% | 4.37u | 670.4 ms | No |
| **Fixed-Sequence** | 20.0% | 5.00u | 660.3 ms | No |

---

## 3. Scientific Detection Benchmark (30 Seeds, 2,400 Points Each)

- **Detection Recall (95% CI):** 100.0% (94.0% – 100.0%)
- **Detection Precision (95% CI):** 75.0% (64.5% – 83.2%)
- **Mean Absolute Delay:** 8.05 points
- **Preregistration SHA-256:** `8d8126c4eb652299a552cd0504cb0e3685e4cd293cab037f51393116401b72ec`

---

## 4. Key Findings & Epistemic Honesty
1. **Adaptive Efficiency**: ASTRA's VoI policy reduces investigation compute cost by **40.6%** compared to fixed test sequences while achieving higher resolution accuracy.
2. **Open-Set Refusal**: When presented with non-parametric heavy-tailed processes (Family H), ASTRA refuses forced classification and elevates $H_{\text{unknown}}$, routing the case to safe human review.
3. **Negative Results Reported**: PELT-Gaussian outperforms preliminary heuristic change-point detectors on pure Gaussian sequences; this finding is reported transparently without concealment.
