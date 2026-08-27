from __future__ import annotations

from typing import Any

from ..datasets import SyntheticMarket, generate_synthetic_market
from .base import DatasetAdapter, DatasetTrack


class SyntheticMarketAdapter(DatasetAdapter):
    """Track A: Controlled Synthetic Market Dataset Adapter."""

    def __init__(self, points: int = 2400, seed: int = 42, signal_amplitude: float = 0.010):
        self._points = points
        self._seed = seed
        self._signal_amplitude = signal_amplitude
        self._cached_data: SyntheticMarket | None = None

    def load(self) -> SyntheticMarket:
        if self._cached_data is None:
            self._cached_data = generate_synthetic_market(
                points=self._points,
                seed=self._seed,
                signal_amplitude=self._signal_amplitude,
            )
        return self._cached_data

    def generate(self, points: int = 2400, seed: int = 42, signal_amplitude: float = 0.010) -> SyntheticMarket:
        return generate_synthetic_market(points=points, seed=seed, signal_amplitude=signal_amplitude)

    @property
    def name(self) -> str:
        return "Synthetic Market v2"

    @property
    def version(self) -> str:
        data = self.load()
        return data.version

    @property
    def track(self) -> DatasetTrack:
        return DatasetTrack.TRACK_A_SYNTHETIC

    @property
    def watermark(self) -> str:
        data = self.load()
        return data.watermark

    @property
    def sha256(self) -> str:
        data = self.load()
        return data.sha256

    @property
    def has_ground_truth(self) -> bool:
        return True

    @property
    def metadata(self) -> dict[str, Any]:
        data = self.load()
        return {
            "source": "In-memory mathematical synthesis (numpy normal & lognormal generators)",
            "license": "MIT (Open Synthetic Benchmark)",
            "points": len(data.returns),
            "seed": self._seed,
            "signal_amplitude": self._signal_amplitude,
            "regime_change_count": len(data.regime_changes),
            "anomaly_count": len(data.anomaly_times),
            "known_limitations": [
                "Generator and detector share Gaussian / variance-jump modeling assumptions.",
                "Discrete time points do not reflect real microsecond latency or order-book queue dynamics.",
            ],
        }
