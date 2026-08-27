# ASTRA v0.3 — STRIDE Threat Model & Security Architecture

---

## 1. STRIDE Threat Analysis Matrix

| STRIDE Category | Threat Description | Affected Component | Implemented Mitigation | Residual Risk | Test Coverage |
|---|---|---|---|---|---|
| **Spoofing** | Presentation of tampered or spoofed datasets as genuine benchmarks. | Ingestion & Dataset Adapters | Explicit watermarking (`SYNTHETIC_ONLY_...`, `REAL_WORLD_...`), version string, and SHA-256 array hashing. | Malicious source file tampering prior to ingestion. | `test_adapters_and_idempotency.py` |
| **Tampering** | Modification of preregistered evaluation thresholds or report contents. | Preregistration & Report Generator | Canonical SHA-256 hashing of `PREREGISTRATION` config embedded into every report and validated against schema. | Manual modification of saved disk files after generation. | `test_scientific_kernel.py` |
| **Repudiation** | Denying which exact model, parameters, or events generated a decision. | Observability & Telemetry | Trace IDs, span IDs, correlation IDs, timestamps, and JSONL event stream for every step. | Operator deleting local log files. | `test_end_to_end_and_reports.py` |
| **Information Disclosure** | Exposure of API keys or sensitive telemetry in artifacts. | Config & Planner | `Settings` loads secrets via environment variables or Secret Manager; secrets are stripped from JSON reports. | Accidental check-in of `.env` files (prevented via `.gitignore`). | Security review & `.gitignore` checks |
| **Denial of Service** | Slow, looping, or computationally expensive tests exhausting CPU. | Investigation Engine & Budget | Strict computational limits (`max_steps=5`, `max_tests=6`, `max_cost_units=10.0`), timeouts, and circuit breaker. | Low-memory container starvation under excessive concurrency. | `test_dsl_and_security.py` |
| **Elevation of Privilege** | LLM planner executing arbitrary Python code or modifying system state. | Planner & Execution Boundary | **Restricted DSL Sandbox**: Planner can only propose approved DSL operations; `DSLValidator` blocks code injection. | Future un-sanitized DSL operations if grammar expands without validation. | `test_dsl_and_security.py` |

---

## 2. Invariants & Autonomous Action Prohibitions

ASTRA operates under strict governance invariants:
1. **No External Autonomous Actions**: ASTRA never executes financial trades, customer account blocks, legal accusations, or unauthorized network transmissions.
2. **Deterministic Rejection**: Unknown DSL operations, out-of-range parameters, and syntax injection tokens are immediately rejected by `DSLValidator`.
3. **Safe Degradation**: When budgets are exhausted or tests fail, ASTRA degrades safely to `DEFER` or `REQUEST_HUMAN_REVIEW`, never to an automated approval.
