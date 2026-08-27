from __future__ import annotations

from typing import Any

from ..contracts import DSLOperation, DSLOperationName, DSLResult, InvestigationHypothesis


class FalsificationEngine:
    """Falsification-first test harness for ASTRA investigations.
    
    Generates targeted tests designed to challenge or disprove candidate hypotheses.
    """

    @classmethod
    def get_adversarial_test(
        cls,
        target_hypothesis: InvestigationHypothesis,
        anomaly_index: int | None = None,
        executed_ops: set[DSLOperationName] | None = None,
    ) -> DSLOperation:
        executed = executed_ops or set()
        hid = target_hypothesis.id

        if hid == "H1":
            # Attempt to falsify transient noise by testing for persistent window contrast or change points
            if DSLOperationName.COMPARE_WINDOWS not in executed and anomaly_index is not None:
                return DSLOperation(
                    op_name=DSLOperationName.COMPARE_WINDOWS,
                    args={"window_size": 100, "center_idx": anomaly_index, "stat": "pooled_contrast"},
                    target_hypotheses=["H1", "H2", "H3"],
                    expected_info_value=0.85,
                    reasoning=f"Adversarial falsification test for H1: check if window contrast at t={anomaly_index} exceeds noise threshold.",
                )
            if DSLOperationName.RUN_PELT not in executed:
                return DSLOperation(
                    op_name=DSLOperationName.RUN_PELT,
                    args={"minimum_segment": 80, "bic_multiplier": 3.0},
                    target_hypotheses=["H1", "H2", "H3"],
                    expected_info_value=0.80,
                    reasoning="Adversarial falsification test for H1: check if optimal partitioning identifies discrete segment changes.",
                )
            return DSLOperation(
                op_name=DSLOperationName.RUN_CUSUM,
                args={"drift": 0.10, "threshold": 12.0, "cooldown": 120},
                target_hypotheses=["H1", "H2"],
                expected_info_value=0.70,
                reasoning="Adversarial test for H1: test for cumulative volatility drift.",
            )

        elif hid == "H2":
            # Attempt to falsify gradual regime change by requiring independent change-point confirmation
            if DSLOperationName.RUN_PELT not in executed:
                return DSLOperation(
                    op_name=DSLOperationName.RUN_PELT,
                    args={"minimum_segment": 80, "bic_multiplier": 3.0},
                    target_hypotheses=["H1", "H2", "H3"],
                    expected_info_value=0.80,
                    reasoning="Adversarial test for H2: check if PELT confirms change-points.",
                )
            if DSLOperationName.CHECK_SUSCEPTIBILITY not in executed:
                return DSLOperation(
                    op_name=DSLOperationName.CHECK_SUSCEPTIBILITY,
                    args={"num_windows": 3},
                    target_hypotheses=["H1", "H2"],
                    expected_info_value=0.75,
                    reasoning="Adversarial test for H2: test if fluctuation susceptibility ratio matches regime transition.",
                )
            return DSLOperation(
                op_name=DSLOperationName.RUN_PAGE_HINKLEY,
                args={"delta": 0.05, "threshold": 18.0, "cooldown": 120},
                target_hypotheses=["H1", "H2", "H3"],
                expected_info_value=0.65,
                reasoning="Adversarial test for H2: verify cumulative mean/variance shift via Page-Hinkley.",
            )

        elif hid == "H3":
            # Attempt to falsify abrupt structural break via BOCPD MAP drop verification
            if DSLOperationName.RUN_BOCPD not in executed:
                return DSLOperation(
                    op_name=DSLOperationName.RUN_BOCPD,
                    args={"hazard_lambda": 500, "minimum_mode_drop": 40, "minimum_separation": 240},
                    target_hypotheses=["H2", "H3"],
                    expected_info_value=0.85,
                    reasoning="Adversarial test for H3: test if BOCPD confirms sharp run-length collapse.",
                )
            return DSLOperation(
                op_name=DSLOperationName.RUN_PELT,
                args={"minimum_segment": 80, "bic_multiplier": 3.0},
                target_hypotheses=["H1", "H3"],
                expected_info_value=0.75,
                reasoning="Adversarial test for H3: verify segment boundary exactness.",
            )

        elif hid == "H4":
            # Attempt to falsify coordinated weak signal via temporal null stacking
            if DSLOperationName.TEST_TEMPORAL_STACKING not in executed:
                return DSLOperation(
                    op_name=DSLOperationName.TEST_TEMPORAL_STACKING,
                    args={"permutations": 999, "alpha": 0.01},
                    target_hypotheses=["H1", "H4"],
                    expected_info_value=0.90,
                    reasoning="Adversarial test for H4: test aligned response against 999 circular-shift temporal null worlds.",
                )
            return DSLOperation(
                op_name=DSLOperationName.REQUEST_FEATURE,
                args={"feature_name": "volume"},
                target_hypotheses=["H1", "H4"],
                expected_info_value=0.60,
                reasoning="Adversarial test for H4: check if event timestamps correlate with volume bursts.",
            )

        else:  # H_unknown
            return DSLOperation(
                op_name=DSLOperationName.CALCULATE_ENTROPY,
                args={"bins": 24},
                target_hypotheses=["H1", "H_unknown"],
                expected_info_value=0.60,
                reasoning="Adversarial test for H_unknown: evaluate macroscopic disorder change.",
            )

    @classmethod
    def evaluate_result(cls, hypothesis_id: str, dsl_result: DSLResult) -> tuple[bool, str]:
        """Evaluates whether the DSLResult contradicts (falsifies/challenges) the hypothesis."""
        if dsl_result.status != "success":
            return False, f"Test {dsl_result.op_name.value} did not complete successfully."

        if hypothesis_id in dsl_result.contradicts:
            return True, f"Test {dsl_result.op_name.value} contradicted {hypothesis_id}."
        elif hypothesis_id in dsl_result.supports:
            return False, f"Test {dsl_result.op_name.value} supported {hypothesis_id}."
        return False, f"Test {dsl_result.op_name.value} was neutral regarding {hypothesis_id}."
