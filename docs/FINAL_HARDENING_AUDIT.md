# ASTRA v0.4.2 — Final Hardening & Baseline Audit

This document establishes the pre-hardening baseline of ASTRA v0.4.1 before executing the final hardening and semantic consistency pass.

---

## 1. Baseline Test & CLI Execution Matrix

| Component | Test / Command | Expected | Actual | Classification | Severity | Action |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **Unit Test Suite** | `python -m unittest discover -s tests -v` | All 78 tests pass | 78 tests passed (8.31s) | `VERIFIED_WORKING` | - | Retain and expand regression suite. |
| **Eligibility Checker** | `python -m astra_poc eligibility-check` | Reports local offline state | `LOCAL OFFLINE VERIFIED` | `VERIFIED_WORKING` | - | Preserve multi-stage state machine. |
| **Google Integration** | `python -m astra_poc integration-test-google` | Graceful test mode if no API key | Offline fake planner passed | `VERIFIED_WORKING` | - | Preserve offline fallback safety. |
| **Google ADK Demo** | `python -m astra_poc google-agent-demo` | Full agent lifecycle | Completed 3 turns, ESCALATE | `VERIFIED_WORKING` | - | Enhance hypothesis delta logging. |
| **Judge Demo** | `python -m astra_poc judge-demo` | Fast demonstration | Decision ESCALATE in <500ms | `VERIFIED_WORKING` | - | Preserve <2 min demo path. |
| **Hero Scenario** | `python -m astra_poc hero-demo` | Falsification & belief shift | Decision ESCALATE (85% H2) | `WORKING_WITH_WARNING` | **P1** | Clarify H1 falsification -> H2/H3 promotion narrative. |
| **Control Scenario** | `python -m astra_poc control-demo` | Safe closure of noise | Decision CLOSE (60% H1) | `VERIFIED_WORKING` | - | Maintain safe closure invariant. |
| **Unknown Scenario (CLI)** | `python -m astra_poc unknown-demo` | Open-set refusal of forced class | Decision DEFER (70% H_unknown) | `VERIFIED_WORKING` | - | Align with API/UI execution path. |
| **Unknown Scenario (UI/API)** | `POST /agent/investigate` (Family H) | Open-set refusal of forced class | Previous run gave H3 80% due to Gaussian changepoint artifact | `SEMANTIC_INCONSISTENT` | **P0** | **Fix root cause**: DSLExecutor must flag non-normality and penalize Gaussian assumptions under heavy tails. |
| **Budget Sensitivity** | `python -m astra_poc budget-demo` | Dynamic budget adaptation | Low=DEFER (1.0u), Med/High=ESCALATE | `VERIFIED_WORKING` | - | Retain VoI sensitivity. |
| **Adversarial Demo** | `python -m astra_poc adversarial-demo` | Stress test handling | Handled cleanly, ESCALATE | `VERIFIED_WORKING` | - | Retain fault injection resilience. |
| **Multimodal Demo** | `python -m astra_poc multimodal-demo` | Cross-check analyst note | `AttributeError: create_mock_analyst_note` | `BUG` | **P1** | **Fix CLI call**: use `ingest_document` / `cross_check_text`. |
| **Fault Recovery** | `python -m astra_poc demo-failures` | Safe boundary blocks faults | 4/4 faults blocked cleanly | `VERIFIED_WORKING` | - | Retain security sandbox. |
| **Pareto Frontier** | `python -m astra_poc pareto-frontier` | Quality-cost trade-off table | Fixed sequence 46.7% vs ASTRA 66.7% | `VERIFIED_WORKING` | - | Generate persistent JSON/CSV benchmark artifacts. |
| **Ablations** | `python -m astra_poc ablations --seeds 3` | Policy ablation evaluation | Executed cleanly across policies | `VERIFIED_WORKING` | - | Retain ablation harness. |
| **Real Market (Track B)** | `python -m astra_poc real-demo` | Empirical dataset evaluation | Executed cleanly, ESCALATE | `VERIFIED_WORKING` | - | Maintain Track B empirical integrity. |
| **Preregistration** | `python -m astra_poc preregistration` | Canonical hash output | `AttributeError: dict has no attribute name` | `BUG` | **P1** | **Fix dict indexing** in CLI. |

---

## 2. Identified Defect Summary

1. **DEF-09 (P0 — Open-Set / Unknown Divergence in Agent/API Execution):**
   - In `DSLExecutor`, standard changepoint algorithms (`RUN_PELT`, `RUN_CUSUM`, `RUN_PAGE_HINKLEY`, `RUN_BOCPD`) assume Gaussian noise. When applied to heavy-tailed Student-$t$ processes (Family H), spurious changepoints are detected, creating false support for $H_3$ / $H_2$.
   - **Fix:** Enhance `DSLExecutor` across changepoint algorithms to evaluate normality/kurtosis; if extreme excess kurtosis (>6.0) or non-parametric heavy tails are present, standard Gaussian changepoint models must be flagged as invalid/spurious, penalizing known hypotheses ($H_1, H_2, H_3$) and supporting $H_{\text{unknown}}$.

2. **DEF-10 (P1 — Multimodal Demo CLI Bug):**
   - `MultimodalEvidenceAdapter` call in `cli.py` used non-existent `create_mock_analyst_note`.
   - **Fix:** Connect `cli.py` to `MultimodalEvidenceAdapter.ingest_document(...)`.

3. **DEF-11 (P1 — Preregistration CLI Dict Indexing Bug):**
   - `cli.py` accessed `PREREGISTRATION_CONFIG.name` instead of `PREREGISTRATION_CONFIG["name"]`.
   - **Fix:** Update dictionary access in `cli.py`.

4. **DEF-12 (P1 — Scenario Registry Drift):**
   - Separate scenario definitions existed in `scenarios.py` and `api.py`.
   - **Fix:** Unify all scenario generation and metadata into a canonical `ScenarioRegistry`.
