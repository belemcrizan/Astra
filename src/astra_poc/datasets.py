from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np


@dataclass(frozen=True)
class SyntheticMarket:
    time: np.ndarray
    returns: np.ndarray
    price: np.ndarray
    volume: np.ndarray
    event_indicator: np.ndarray
    template: np.ndarray
    regime_changes: tuple[int, ...]
    event_times: tuple[int, ...]
    anomaly_times: tuple[int, ...]
    version: str
    seed: int
    watermark: str
    sha256: str
    signal_amplitude: float


def generate_synthetic_market(points: int = 2400, seed: int = 42, signal_amplitude: float = 0.010) -> SyntheticMarket:
    """Creates three regimes, repeated weak responses and isolated anomalies.

    Ground truth is retained only for evaluation. Analytical agents receive the
    observed arrays and the event indicator, not the hidden change/anomaly labels.
    """
    rng = np.random.default_rng(seed)
    first, second = round(points * 0.30), round(points * 0.66)
    regime_changes = (first, second)
    returns = np.empty(points, dtype=float)
    segments = (
        (0, first, 0.0001, 0.006),
        (first, second, -0.00015, 0.015),
        (second, points, 0.00035, 0.008),
    )
    for start, end, drift, volatility in segments:
        returns[start:end] = rng.normal(drift, volatility, end - start)

    # A domain-specific weak response: brief drop followed by slower rebound.
    template = np.array([-0.15, -0.55, -1.0, -0.70, -0.20, 0.35, 0.72, 0.48, 0.18])
    event_times = (round(points * 0.19), round(points * 0.48), round(points * 0.79))
    event_indicator = np.zeros(points, dtype=int)
    for event in event_times:
        event_indicator[event] = 1
        end = min(points, event + template.size)
        returns[event:end] += signal_amplitude * template[: end - event]

    anomaly_times = (round(points * 0.37), round(points * 0.58))
    # Absolute values avoid a random draw cancelling the injected ground truth.
    returns[anomaly_times[0]] = 0.095
    returns[anomaly_times[1]] = -0.105

    price = 100.0 * np.exp(np.cumsum(returns))
    regime_vol = np.where(np.arange(points) < first, 1.0, np.where(np.arange(points) < second, 2.0, 1.25))
    volume = rng.lognormal(mean=11.0, sigma=0.22, size=points) * regime_vol
    volume[list(anomaly_times)] *= 3.0
    digest = hashlib.sha256()
    for array in (returns, price, volume, event_indicator):
        digest.update(np.ascontiguousarray(array).tobytes())
    return SyntheticMarket(
        time=np.arange(points), returns=returns, price=price, volume=volume,
        event_indicator=event_indicator, template=template,
        regime_changes=regime_changes, event_times=event_times,
        anomaly_times=anomaly_times, version=f"synthetic-market-v2-seed-{seed}-n-{points}-a-{signal_amplitude:.6f}",
        seed=seed, watermark="SYNTHETIC_ONLY_NOT_REAL_DATA", sha256=digest.hexdigest(),
        signal_amplitude=signal_amplitude,
    )
