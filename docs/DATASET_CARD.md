# ASTRA v0.3 — Dataset Cards (Track A & Track B)

---

## Track A: Synthetic Market Dataset (v2)

### 1. Purpose
Designed for controlled statistical sanity testing, baseline comparison, and evaluation of anomaly detection algorithms with verified mathematical ground truth.

### 2. Composition & Generation
- **Series Length:** 2,400 observations (configurable $\ge 600$).
- **Regime Dynamics:** 3 Gaussian regimes with distinct mean return and volatility parameters.
- **Anomalies:** 2 isolated point anomalies with controlled injection magnitudes.
- **Weak Signal Waveform:** 3 discrete events preceding an aligned 9-step template response ($[-0.15, -0.55, -1.0, -0.70, -0.20, 0.35, 0.72, 0.48, 0.18]$).
- **Price & Volume:** Price generated via exponential cumulative return summation; volume drawn from lognormal distribution conditioned on volatility regime.

### 3. Provenance & Security
- **Watermark:** `SYNTHETIC_ONLY_NOT_REAL_DATA`
- **Integrity Hash:** Canonical SHA-256 computed across returns, price, volume, and event indicator arrays.
- **Ground Truth Availability:** Hidden from analytical agents; retained exclusively by the evaluation module.

### 4. Known Limitations
- Generator and statistical detectors share parametric assumptions (Gaussian / variance clustering).
- Discrete time steps do not represent microsecond limit order book physics.

---

## Track B: Real-World Volatility Shock Benchmark Series

### 1. Purpose
Evaluates ASTRA's investigation capabilities on empirical market telemetry exhibiting real-world fat tails, volatility clustering, and flash shocks, without manufacturing synthetic ground truth.

### 2. Composition
- **Source:** Historical public benchmark market volatility series (March 2020 market regime shock episode).
- **License:** CC0 1.0 Universal (Public Domain Dedication).
- **Length:** 1,200 observations.
- **Features:** Returns, Price, Volume.

### 3. Provenance & Epistemic Rules
- **Watermark:** `REAL_WORLD_EXTERNAL_DATA_NO_GROUND_TRUTH`
- **Integrity SHA-256:** `c384ec1f5195b9b69171fcb63fbb7e9bb5fe19788fe6b475236bfd9200e91c7f`
- **Zero-Ground-Truth Discipline:** ASTRA does NOT claim precision or recall against real datasets because true change-point dates cannot be known with 100% certainty. Only observable test behaviors, cost, and decision stability are reported.

### 4. Known Limitations
- Contains unmodeled exogenous factors, macro news announcements, and liquidity variations.
