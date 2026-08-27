# ASTRA v0.3 — Agents, Statistical Methods & DSL Operations

---

## 1. Analytical Agents & Detectors

| Component | Responsibility | Input | Core Statistical Method | Output |
|---|---|---|---|---|
| **Signal Agent** | Detects local spike anomalies and matched filter peaks. | Returns, Template | Robust Z-score ($1.4826 \times \text{MAD}$) & sliding-window normalized cross-correlation. | Anomaly indices, candidate peaks, SNR. |
| **Regime Agent** | Detects variance and mean shifts. | Returns | Local window mean shift + log standard deviation ratio contrast. | Candidate change-points. |
| **Physics Agent** | Measures physical / information observables. | Returns | Shannon histogram entropy, extensive fluctuation susceptibility ($N \cdot \text{Var}$), lag-1 autocorrelation, and relaxation time. | Macroscopic system observables. |
| **Graph Agent** | Maps temporal event adjacency without assuming intent. | Event indicator, Returns | Temporal edge window mapping ($\Delta t \le 16$). | Event coverage, edge counts. |
| **Causal / Response Agent** | Tests weak response alignment against temporal null. | Returns, Event indicator, Template | 999 circular-shift empirical null permutations with Benjamini-Hochberg ranking. | Empirical p-value, SNR, null mean/std. |

---

## 2. Investigation & Governance Components

| Component | Responsibility | Method |
|---|---|---|
| **Investigation State Machine** | Enforces valid lifecycle state transitions and prevents illegal bypasses. | Formal deterministic transition table with guard conditions. |
| **Hypothesis Pool** | Manages competing explanations ($H_1$ to $H_4$ and $H_{\text{unknown}}$). | Dynamic evidence score updating, status tracking, and falsification logs. |
| **Discriminative Evidence Selector** | Chooses the most informative test for top hypothesis competitors. | Expected information gain per unit cost heuristic: $\max \frac{E[I]}{C}$. |
| **Falsification Engine** | Generates adversarial tests designed to challenge or disprove candidate hypotheses. | Falsification-first test routing and outcome evaluation. |
| **DSL Validator & Sandbox** | Restricts execution to approved numerical operations. | Schema validation, parameter bounds checking, injection defense, budget enforcement. |
| **Decision Policy** | Maps accumulated evidence to final action with reason codes. | Multi-factor rule table emitting `CLOSE`, `WATCH`, `ESCALATE`, `DEFER`, or `REQUEST_HUMAN_REVIEW`. |
