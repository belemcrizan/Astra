from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..contracts import DSLOperationName


@dataclass(frozen=True)
class DSLParamSpec:
    name: str
    type_name: str  # "float", "int", "str", "bool"
    min_value: float | int | None = None
    max_value: float | int | None = None
    allowed_values: list[str] | None = None
    default: Any = None
    required: bool = False


@dataclass(frozen=True)
class DSLOperationSpec:
    name: DSLOperationName
    description: str
    params: dict[str, DSLParamSpec] = field(default_factory=dict)
    cost_units: float = 1.0
    discriminates: list[str] = field(default_factory=list)  # e.g., ["H1", "H2"]


# Formal DSL Specification for ASTRA v0.3
DSL_OPERATION_SPECS: dict[DSLOperationName, DSLOperationSpec] = {
    DSLOperationName.RUN_CUSUM: DSLOperationSpec(
        name=DSLOperationName.RUN_CUSUM,
        description="Run two-sided CUSUM change detector on robust volatility feature.",
        params={
            "drift": DSLParamSpec("drift", "float", min_value=0.01, max_value=2.0, default=0.10),
            "threshold": DSLParamSpec("threshold", "float", min_value=1.0, max_value=50.0, default=12.0),
            "cooldown": DSLParamSpec("cooldown", "int", min_value=10, max_value=500, default=120),
        },
        cost_units=1.0,
        discriminates=["H1", "H2"],
    ),
    DSLOperationName.RUN_PAGE_HINKLEY: DSLOperationSpec(
        name=DSLOperationName.RUN_PAGE_HINKLEY,
        description="Run Page-Hinkley cumulative change-point detector.",
        params={
            "delta": DSLParamSpec("delta", "float", min_value=0.001, max_value=1.0, default=0.05),
            "threshold": DSLParamSpec("threshold", "float", min_value=1.0, max_value=50.0, default=18.0),
            "cooldown": DSLParamSpec("cooldown", "int", min_value=10, max_value=500, default=120),
        },
        cost_units=1.0,
        discriminates=["H1", "H2", "H3"],
    ),
    DSLOperationName.RUN_PELT: DSLOperationSpec(
        name=DSLOperationName.RUN_PELT,
        description="Run Pruned Exact Linear Time optimal partitioning with Gaussian segment cost.",
        params={
            "minimum_segment": DSLParamSpec("minimum_segment", "int", min_value=10, max_value=500, default=80),
            "bic_multiplier": DSLParamSpec("bic_multiplier", "float", min_value=0.5, max_value=10.0, default=3.0),
        },
        cost_units=2.0,
        discriminates=["H1", "H2", "H3"],
    ),
    DSLOperationName.RUN_BOCPD: DSLOperationSpec(
        name=DSLOperationName.RUN_BOCPD,
        description="Run Bayesian Online Change Point Detection with Normal-Inverse-Gamma conjugate prior.",
        params={
            "hazard_lambda": DSLParamSpec("hazard_lambda", "int", min_value=50, max_value=5000, default=500),
            "minimum_mode_drop": DSLParamSpec("minimum_mode_drop", "int", min_value=5, max_value=200, default=40),
            "minimum_separation": DSLParamSpec("minimum_separation", "int", min_value=10, max_value=500, default=240),
        },
        cost_units=3.0,
        discriminates=["H2", "H3"],
    ),
    DSLOperationName.COMPARE_WINDOWS: DSLOperationSpec(
        name=DSLOperationName.COMPARE_WINDOWS,
        description="Compare adjacent sub-windows across a proposed change-point.",
        params={
            "window_size": DSLParamSpec("window_size", "int", min_value=20, max_value=500, default=100),
            "center_idx": DSLParamSpec("center_idx", "int", min_value=20, max_value=100000, default=720),
            "stat": DSLParamSpec("stat", "str", allowed_values=["mean_shift", "vol_shift", "pooled_contrast"], default="pooled_contrast"),
        },
        cost_units=1.0,
        discriminates=["H1", "H2", "H3"],
    ),
    DSLOperationName.CALCULATE_ENTROPY: DSLOperationSpec(
        name=DSLOperationName.CALCULATE_ENTROPY,
        description="Calculate Shannon entropy across window partitions to measure disorder shift.",
        params={
            "bins": DSLParamSpec("bins", "int", min_value=5, max_value=100, default=24),
        },
        cost_units=0.5,
        discriminates=["H1", "H2"],
    ),
    DSLOperationName.CHECK_SUSCEPTIBILITY: DSLOperationSpec(
        name=DSLOperationName.CHECK_SUSCEPTIBILITY,
        description="Calculate extensive fluctuation ratio across partitions.",
        params={
            "num_windows": DSLParamSpec("num_windows", "int", min_value=2, max_value=10, default=3),
        },
        cost_units=0.5,
        discriminates=["H1", "H2"],
    ),
    DSLOperationName.TEST_TEMPORAL_STACKING: DSLOperationSpec(
        name=DSLOperationName.TEST_TEMPORAL_STACKING,
        description="Run event stacking with circular time-shift empirical temporal null.",
        params={
            "permutations": DSLParamSpec("permutations", "int", min_value=50, max_value=2000, default=999),
            "alpha": DSLParamSpec("alpha", "float", min_value=0.001, max_value=0.1, default=0.01),
        },
        cost_units=2.5,
        discriminates=["H1", "H4"],
    ),
    DSLOperationName.REQUEST_FEATURE: DSLOperationSpec(
        name=DSLOperationName.REQUEST_FEATURE,
        description="Request secondary diagnostic feature (e.g., volume profile, lag-1 autocorrelation).",
        params={
            "feature_name": DSLParamSpec("feature_name", "str", allowed_values=["volume", "returns", "price", "lag1_autocorr"], default="volume"),
        },
        cost_units=0.5,
        discriminates=["H1", "H_unknown"],
    ),
    DSLOperationName.EVALUATE_HYPOTHESIS: DSLOperationSpec(
        name=DSLOperationName.EVALUATE_HYPOTHESIS,
        description="Explicitly score and evaluate hypothesis based on accumulated evidence.",
        params={
            "hypothesis_id": DSLParamSpec("hypothesis_id", "str", allowed_values=["H1", "H2", "H3", "H4", "H_unknown"], required=True),
        },
        cost_units=0.2,
        discriminates=[],
    ),
    DSLOperationName.RECOMMEND_DECISION: DSLOperationSpec(
        name=DSLOperationName.RECOMMEND_DECISION,
        description="Propose investigation termination decision and reason code.",
        params={
            "decision": DSLParamSpec("decision", "str", allowed_values=["CLOSE", "WATCH", "ESCALATE", "DEFER", "REQUEST_HUMAN_REVIEW"], required=True),
            "reason_code": DSLParamSpec("reason_code", "str", required=True),
        },
        cost_units=0.0,
        discriminates=[],
    ),
}

ALLOWED_DSL_OPERATIONS = set(DSL_OPERATION_SPECS.keys())
