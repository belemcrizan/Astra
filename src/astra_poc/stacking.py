from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class StackingResult:
    event_count: int
    horizon: int
    observed_statistic: float
    null_mean: float
    null_standard_deviation: float
    empirical_snr: float
    p_value: float
    permutations: int
    null_method: str
    significant: bool
    alpha: float
    stacked_response: list[float]

    def to_dict(self) -> dict:
        return asdict(self)


def _circular_windows(values: np.ndarray, positions: np.ndarray, horizon: int) -> np.ndarray:
    offsets = np.arange(horizon)
    indices = (positions[:, None] + offsets[None, :]) % len(values)
    return values[indices]


def event_stacking_test(
    values: np.ndarray,
    event_indicator: np.ndarray,
    template: np.ndarray,
    *,
    permutations: int,
    alpha: float,
    seed: int,
) -> StackingResult:
    """Matched stacking with a circular-shift empirical temporal null.

    Circular shifts preserve the return series, its autocorrelation and its
    volatility clustering. Only the alignment between events and returns is
    broken. This is stronger than freely shuffling timestamps.
    """
    events = np.flatnonzero(event_indicator)
    horizon = len(template)
    if len(events) < 2:
        raise ValueError("Stacking requires at least two events.")
    normalized_template = template - template.mean()
    normalized_template /= max(np.linalg.norm(normalized_template), 1e-12)
    observed_windows = _circular_windows(values, events, horizon)
    per_event = observed_windows @ normalized_template
    observed = float(per_event.mean())

    rng = np.random.default_rng(seed + 10_007)
    allowed = np.arange(2 * horizon, len(values) - 2 * horizon)
    replace = permutations > len(allowed)
    shifts = rng.choice(allowed, size=permutations, replace=replace)
    null = np.empty(permutations, dtype=float)
    for index, shift in enumerate(shifts):
        shifted = (events + int(shift)) % len(values)
        null[index] = float((_circular_windows(values, shifted, horizon) @ normalized_template).mean())
    p_value = float((1 + np.count_nonzero(null >= observed)) / (permutations + 1))
    null_std = float(null.std(ddof=1))
    empirical_snr = float((observed - null.mean()) / max(null_std, 1e-12))
    return StackingResult(
        event_count=len(events), horizon=horizon, observed_statistic=observed,
        null_mean=float(null.mean()), null_standard_deviation=null_std,
        empirical_snr=empirical_snr, p_value=p_value, permutations=permutations,
        null_method="circular_time_shift", significant=p_value <= alpha, alpha=alpha,
        stacked_response=observed_windows.mean(axis=0).tolist(),
    )

