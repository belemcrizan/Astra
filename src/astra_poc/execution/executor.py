from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from ..baselines import bocpd_baseline, cusum_baseline, page_hinkley_baseline, pelt_baseline
from ..contracts import DSLOperation, DSLOperationName, DSLResult, EvidenceItem
from ..stacking import event_stacking_test


class DSLExecutor:
    """Deterministic, sandboxed executor for validated ASTRA DSL operations."""

    def __init__(self, data: Any):
        self.data = data
        self.returns = np.asarray(getattr(data, "returns", data), dtype=float)
        self.price = getattr(data, "price", None)
        self.volume = getattr(data, "volume", None)
        self.event_indicator = getattr(data, "event_indicator", None)
        self.template = getattr(data, "template", None)
        self.seed = getattr(data, "seed", 42)

    def _is_heavy_tailed_open_set(self) -> tuple[bool, float]:
        """Calculates excess kurtosis to detect non-parametric heavy-tailed / Cauchy regimes."""
        if len(self.returns) < 20:
            return False, 0.0
        std = self.returns.std()
        if std < 1e-12:
            return False, 0.0
        norm_r = (self.returns - self.returns.mean()) / std
        kurt = float(np.mean(norm_r**4) - 3.0)
        return kurt > 6.0, kurt

    def execute(self, operation: DSLOperation) -> DSLResult:
        started = time.perf_counter()
        op_name = operation.op_name
        args = operation.args or {}

        try:
            is_ht, overall_kurt = self._is_heavy_tailed_open_set()

            if op_name == DSLOperationName.RUN_CUSUM:
                res = cusum_baseline(self.returns, **args)
                cps = res.change_points
                has_cps = len(cps) > 0
                if is_ht:
                    ev = EvidenceItem(
                        code="CUSUM_HEAVY_TAIL_SPURIOUS",
                        statement=f"CUSUM detected {len(cps)} potential triggers, but series exhibits extreme excess kurtosis ({overall_kurt:.2f} > 6.0), indicating spurious detections under non-parametric open-set dynamics.",
                        value=round(overall_kurt, 2),
                        threshold=6.0,
                        passed=True,
                        hypotheses_discriminated=["H1", "H2", "H3", "H_unknown"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H_unknown"]
                    contradicts = ["H1", "H2", "H3", "H4"]
                else:
                    ev = EvidenceItem(
                        code="CUSUM_DETECTIONS",
                        statement=f"CUSUM detected {len(cps)} volatility change-points.",
                        value=len(cps),
                        threshold=1,
                        passed=has_cps,
                        hypotheses_discriminated=["H1", "H2"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H2", "H3"] if has_cps else ["H1"]
                    contradicts = ["H1"] if has_cps else ["H2", "H3"]
                return self._build_result(operation, res.to_dict(), [ev], supports, contradicts, started)

            elif op_name == DSLOperationName.RUN_PAGE_HINKLEY:
                res = page_hinkley_baseline(self.returns, **args)
                cps = res.change_points
                has_cps = len(cps) > 0
                if is_ht:
                    ev = EvidenceItem(
                        code="PAGE_HINKLEY_HEAVY_TAIL_SPURIOUS",
                        statement=f"Page-Hinkley detected {len(cps)} cumulative change-points, but series exhibits extreme excess kurtosis ({overall_kurt:.2f} > 6.0), indicating heavy-tailed open-set process.",
                        value=round(overall_kurt, 2),
                        threshold=6.0,
                        passed=True,
                        hypotheses_discriminated=["H1", "H2", "H3", "H_unknown"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H_unknown"]
                    contradicts = ["H1", "H2", "H3", "H4"]
                else:
                    ev = EvidenceItem(
                        code="PAGE_HINKLEY_DETECTIONS",
                        statement=f"Page-Hinkley detected {len(cps)} cumulative change-points.",
                        value=len(cps),
                        threshold=1,
                        passed=has_cps,
                        hypotheses_discriminated=["H1", "H2", "H3"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H2", "H3"] if has_cps else ["H1"]
                    contradicts = ["H1"] if has_cps else ["H2", "H3"]
                return self._build_result(operation, res.to_dict(), [ev], supports, contradicts, started)

            elif op_name == DSLOperationName.RUN_PELT:
                res = pelt_baseline(self.returns, **args)
                cps = res.change_points
                has_cps = len(cps) > 0
                if is_ht:
                    ev = EvidenceItem(
                        code="PELT_HEAVY_TAIL_SPURIOUS",
                        statement=f"PELT exact partitioning identified {len(cps)} segment boundaries, but series exhibits extreme excess kurtosis ({overall_kurt:.2f} > 6.0), violating Gaussian model assumptions.",
                        value=round(overall_kurt, 2),
                        threshold=6.0,
                        passed=True,
                        hypotheses_discriminated=["H1", "H2", "H3", "H_unknown"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H_unknown"]
                    contradicts = ["H1", "H2", "H3", "H4"]
                else:
                    ev = EvidenceItem(
                        code="PELT_DETECTIONS",
                        statement=f"PELT exact partitioning identified {len(cps)} optimal segment boundaries.",
                        value=len(cps),
                        threshold=1,
                        passed=has_cps,
                        hypotheses_discriminated=["H1", "H2", "H3"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H3", "H2"] if has_cps else ["H1"]
                    contradicts = ["H1"] if has_cps else ["H3", "H2"]
                return self._build_result(operation, res.to_dict(), [ev], supports, contradicts, started)

            elif op_name == DSLOperationName.RUN_BOCPD:
                res = bocpd_baseline(self.returns, **args)
                cps = res.change_points
                has_cps = len(cps) > 0
                if is_ht:
                    ev = EvidenceItem(
                        code="BOCPD_HEAVY_TAIL_SPURIOUS",
                        statement=f"BOCPD detected {len(cps)} MAP run-length collapses under heavy-tailed non-Gaussian distribution ({overall_kurt:.2f} > 6.0).",
                        value=round(overall_kurt, 2),
                        threshold=6.0,
                        passed=True,
                        hypotheses_discriminated=["H1", "H2", "H3", "H_unknown"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H_unknown"]
                    contradicts = ["H1", "H2", "H3", "H4"]
                else:
                    ev = EvidenceItem(
                        code="BOCPD_DETECTIONS",
                        statement=f"BOCPD detected {len(cps)} MAP run-length collapses.",
                        value=len(cps),
                        threshold=1,
                        passed=has_cps,
                        hypotheses_discriminated=["H2", "H3"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H2", "H3"] if has_cps else ["H1"]
                    contradicts = ["H1"] if has_cps else ["H2", "H3"]
                return self._build_result(operation, res.to_dict(), [ev], supports, contradicts, started)

            elif op_name == DSLOperationName.COMPARE_WINDOWS:
                w = args["window_size"]
                c = min(max(args["center_idx"], w), len(self.returns) - w)
                left, right = self.returns[c - w : c], self.returns[c : c + w]
                pooled_std = math.sqrt((left.var() + right.var()) / 2 + 1e-12)
                mean_shift = abs(left.mean() - right.mean()) / pooled_std
                vol_ratio = (right.std() + 1e-12) / (left.std() + 1e-12)
                vol_shift = abs(math.log(vol_ratio))
                score = mean_shift + 1.8 * vol_shift
                is_shift = score >= 0.75

                # Detect non-parametric heavy-tailed process outside Gaussian assumptions
                combined_window = np.concatenate([left, right])
                kurtosis = float(np.mean(((combined_window - combined_window.mean()) / (combined_window.std() + 1e-12))**4) - 3.0)
                is_heavy_tailed = kurtosis > 8.0

                if is_heavy_tailed:
                    ev = EvidenceItem(
                        code="HEAVY_TAIL_EXCESS",
                        statement=f"Sub-window at t={c} exhibits extreme excess kurtosis {kurtosis:.2f} (> 8.0), violating Gaussian/AR assumptions.",
                        value=round(kurtosis, 2),
                        threshold=8.0,
                        passed=True,
                        hypotheses_discriminated=["H1", "H2", "H_unknown"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H_unknown"]
                    contradicts = ["H1", "H2"]
                else:
                    ev = EvidenceItem(
                        code="WINDOW_CONTRAST",
                        statement=f"Sub-window comparison at t={c} yielded contrast score {score:.3f} (mean shift={mean_shift:.3f}, vol shift={vol_shift:.3f}).",
                        value=round(score, 4),
                        threshold=0.75,
                        passed=is_shift,
                        hypotheses_discriminated=["H1", "H2", "H3"],
                        why_selected=operation.reasoning,
                        cost_units=operation.cost_units,
                    )
                    supports = ["H2", "H3"] if is_shift else ["H1"]
                    contradicts = ["H1"] if is_shift else ["H2", "H3"]

                return self._build_result(
                    operation,
                    {"center": c, "contrast_score": score, "mean_shift": mean_shift, "vol_shift": vol_shift, "kurtosis": kurtosis},
                    [ev],
                    supports,
                    contradicts,
                    started,
                )

            elif op_name == DSLOperationName.CALCULATE_ENTROPY:
                bins = args["bins"]
                windows = np.array_split(self.returns, 3)
                entropies = []
                for part in windows:
                    hist, _ = np.histogram(part, bins=bins)
                    probs = hist[hist > 0] / hist.sum()
                    entropies.append(float(-(probs * np.log(probs)).sum()))
                max_diff = max(entropies) - min(entropies)
                is_disorder_shift = max_diff > 0.20
                is_extreme_disorder = max_diff > 0.45

                ev = EvidenceItem(
                    code="ENTROPY_DIFFERENTIAL",
                    statement=f"Partition entropy variation is {max_diff:.4f} across 3 segments.",
                    value=round(max_diff, 4),
                    threshold=0.20,
                    passed=is_disorder_shift,
                    hypotheses_discriminated=["H1", "H2", "H_unknown"],
                    why_selected=operation.reasoning,
                    cost_units=operation.cost_units,
                )
                if is_extreme_disorder:
                    supports = ["H_unknown"]
                    contradicts = ["H1", "H2"]
                elif is_disorder_shift:
                    supports = ["H2"]
                    contradicts = ["H1"]
                else:
                    supports = ["H1"]
                    contradicts = ["H2", "H_unknown"]
                return self._build_result(operation, {"entropies": entropies, "max_diff": max_diff}, [ev], supports, contradicts, started)

            elif op_name == DSLOperationName.CHECK_SUSCEPTIBILITY:
                windows = np.array_split(self.returns, args["num_windows"])
                susceptibilities = [float(np.var(part) * len(part)) for part in windows]
                ratio = max(susceptibilities) / max(min(susceptibilities), 1e-12)
                is_high_ratio = ratio >= 2.0
                is_extreme_ratio = ratio >= 15.0

                ev = EvidenceItem(
                    code="SUSCEPTIBILITY_RATIO",
                    statement=f"Fluctuation susceptibility ratio between partitions is {ratio:.2f}.",
                    value=round(ratio, 3),
                    threshold=2.0,
                    passed=is_high_ratio,
                    hypotheses_discriminated=["H1", "H2", "H_unknown"],
                    why_selected=operation.reasoning,
                    cost_units=operation.cost_units,
                )
                if is_extreme_ratio:
                    supports = ["H_unknown"]
                    contradicts = ["H1", "H2"]
                elif is_high_ratio:
                    supports = ["H2"]
                    contradicts = ["H1"]
                else:
                    supports = ["H1"]
                    contradicts = ["H2", "H_unknown"]
                return self._build_result(operation, {"susceptibilities": susceptibilities, "ratio": ratio}, [ev], supports, contradicts, started)

            elif op_name == DSLOperationName.TEST_TEMPORAL_STACKING:
                if self.event_indicator is None or self.template is None or np.count_nonzero(self.event_indicator) < 2:
                    # Synthetic fallback if events not explicit
                    ev = EvidenceItem(
                        code="STACKING_SKIPPED",
                        statement="Insufficient discrete event markers available for temporal null stacking.",
                        value=None,
                        passed=False,
                        hypotheses_discriminated=["H1", "H4"],
                        cost_units=operation.cost_units,
                    )
                    return self._build_result(operation, {"skipped": True}, [ev], ["H1"], ["H4"], started)

                stack_res = event_stacking_test(
                    self.returns,
                    self.event_indicator,
                    self.template,
                    permutations=args["permutations"],
                    alpha=args["alpha"],
                    seed=self.seed,
                )
                is_sig = stack_res.significant
                ev = EvidenceItem(
                    code="STACKING_EMPIRICAL_P_VALUE",
                    statement=f"Empirical temporal null p-value is {stack_res.p_value:.5f} (alpha={args['alpha']}, SNR={stack_res.empirical_snr:.2f}).",
                    value=round(stack_res.p_value, 5),
                    threshold=args["alpha"],
                    passed=is_sig,
                    hypotheses_discriminated=["H1", "H4"],
                    why_selected=operation.reasoning,
                    cost_units=operation.cost_units,
                )
                supports = ["H4"] if is_sig else ["H1"]
                contradicts = ["H1"] if is_sig else ["H4"]
                return self._build_result(operation, stack_res.to_dict(), [ev], supports, contradicts, started)

            elif op_name == DSLOperationName.REQUEST_FEATURE:
                fname = args["feature_name"]
                if fname == "volume" and self.volume is not None:
                    vol_z = float((self.volume.max() - self.volume.mean()) / (self.volume.std() + 1e-12))
                    ev = EvidenceItem(
                        code="VOLUME_SPIKE_RATIO",
                        statement=f"Peak volume Z-score is {vol_z:.2f}.",
                        value=round(vol_z, 3),
                        threshold=3.0,
                        passed=vol_z >= 3.0,
                        hypotheses_discriminated=["H1", "H_unknown"],
                        cost_units=operation.cost_units,
                    )
                    supports = ["H3", "H_unknown"] if vol_z >= 3.0 else ["H1"]
                    contradicts = ["H1"] if vol_z >= 3.0 else ["H3"]
                    return self._build_result(operation, {"peak_volume_z": vol_z}, [ev], supports, contradicts, started)
                else:
                    ev = EvidenceItem(
                        code="FEATURE_REQUEST",
                        statement=f"Feature '{fname}' summary computed.",
                        value=float(np.std(self.returns)),
                        passed=True,
                        hypotheses_discriminated=["H1", "H_unknown"],
                        cost_units=operation.cost_units,
                    )
                    return self._build_result(operation, {"feature": fname}, [ev], ["H1"], [], started)

            elif op_name == DSLOperationName.EVALUATE_HYPOTHESIS:
                hid = args["hypothesis_id"]
                ev = EvidenceItem(
                    code="HYPOTHESIS_EVALUATION",
                    statement=f"Hypothesis {hid} evaluation trigger processed.",
                    value=hid,
                    passed=True,
                    hypotheses_discriminated=[hid],
                    cost_units=operation.cost_units,
                )
                return self._build_result(operation, {"hypothesis_id": hid}, [ev], [hid], [], started)

            elif op_name == DSLOperationName.RECOMMEND_DECISION:
                ev = EvidenceItem(
                    code="DECISION_RECOMMENDATION",
                    statement=f"Recommended decision {args['decision']} with reason {args['reason_code']}.",
                    value=args["decision"],
                    passed=True,
                    cost_units=0.0,
                )
                return self._build_result(operation, args, [ev], [], [], started)

            else:
                return DSLResult(
                    op_name=op_name,
                    status="failed",
                    error=f"Unhandled operation executor dispatch: {op_name}",
                    latency_ms=(time.perf_counter() - started) * 1000,
                )

        except Exception as exc:
            return DSLResult(
                op_name=op_name,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=(time.perf_counter() - started) * 1000,
            )

    def _build_result(
        self,
        op: DSLOperation,
        observed_value: Any,
        evidence_items: list[EvidenceItem],
        supports: list[str],
        contradicts: list[str],
        started_perf: float,
    ) -> DSLResult:
        elapsed = (time.perf_counter() - started_perf) * 1000
        for item in evidence_items:
            item.latency_ms = round(elapsed, 3)
        return DSLResult(
            op_name=op.op_name,
            status="success",
            observed_value=observed_value,
            evidence_generated=evidence_items,
            supports=supports,
            contradicts=contradicts,
            cost_units=op.cost_units,
            latency_ms=round(elapsed, 3),
        )
