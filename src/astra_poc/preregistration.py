from __future__ import annotations

import hashlib
import json
from typing import Any

# Thresholds are code-versioned and hashed into every report. Changing a value
# creates a different methodology identity and must be reported explicitly.
PREREGISTRATION: dict[str, Any] = {
    "methodology_version": "astra-scientific-v0.3.0",
    "evaluation": {
        "change_tolerance_fraction": 0.035,
        "anomaly_tolerance_points": 2,
        "confidence_level": 0.95,
        "matching": "one_to_one_minimum_absolute_delay",
    },
    "signal": {
        "robust_z_threshold": 7.0,
        "matched_candidate_z": 2.2,
        "maximum_matched_candidates": 8,
    },
    "regime": {
        "window": 100,
        "minimum_separation": 240,
        "change_score_threshold": 0.75,
        "maximum_candidates": 8,
    },
    "stacking": {
        "null_method": "circular_time_shift",
        "permutations": 999,
        "alpha": 0.01,
        "alternative": "greater",
        "multiple_testing": "benjamini_hochberg_when_multiple_hypotheses",
    },
    "baselines": {
        "cusum": {"drift": 0.10, "threshold": 12.0, "cooldown": 120},
        "page_hinkley": {"delta": 0.05, "threshold": 18.0, "cooldown": 120},
        "pelt": {"minimum_segment": 80, "bic_multiplier": 3.0},
        "bocpd": {"hazard_lambda": 500, "minimum_mode_drop": 40, "minimum_separation": 240},
    },
    "investigation": {
        "min_evidence_score": 0.60,
        "max_steps": 5,
        "max_tests": 6,
        "max_cost_units": 10.0,
        "state_machine": "formal_bounded_lifecycle",
        "dsl_grammar": "astra_restricted_dsl_v1",
        "competing_hypotheses": ["H1", "H2", "H3", "H4", "H_unknown"],
        "falsification_first": True,
    },
}


def preregistration_hash() -> str:
    canonical = json.dumps(PREREGISTRATION, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
