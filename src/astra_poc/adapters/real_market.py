from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .base import DatasetAdapter, DatasetTrack


@dataclass(frozen=True)
class RealMarketData:
    time: np.ndarray
    returns: np.ndarray
    price: np.ndarray
    volume: np.ndarray
    version: str
    watermark: str
    sha256: str
    event_indicator: np.ndarray | None = None
    template: np.ndarray | None = None
    seed: int = 0


class RealMarketAdapter(DatasetAdapter):
    """Track B: External Real-World Dataset Adapter.
    
    Operates under strict epistemic discipline:
    Does NOT manufacture synthetic ground-truth labels for real data.
    """

    def __init__(self, fixture_path: str | Path | None = None):
        self._fixture_path = Path(fixture_path) if fixture_path else Path(__file__).parents[3] / "fixtures" / "real_world_market_sample.json"
        self._cached_data: RealMarketData | None = None
        self._raw_json: dict[str, Any] = {}

    def load(self) -> RealMarketData:
        if self._cached_data is None:
            if not self._fixture_path.exists():
                raise FileNotFoundError(f"Real-world fixture not found at: {self._fixture_path}")
            
            with self._fixture_path.open("r", encoding="utf-8") as stream:
                self._raw_json = json.load(stream)

            returns = np.array(self._raw_json["returns"], dtype=float)
            price = np.array(self._raw_json["price"], dtype=float)
            volume = np.array(self._raw_json["volume"], dtype=float)
            n = len(returns)

            self._cached_data = RealMarketData(
                time=np.arange(n),
                returns=returns,
                price=price,
                volume=volume,
                version=self._raw_json.get("version", "real-world-dataset-v1"),
                watermark=self._raw_json.get("watermark", "REAL_WORLD_EXTERNAL_DATA_NO_GROUND_TRUTH"),
                sha256=self._raw_json.get("sha256", "unknown"),
                event_indicator=None,
                template=None,
                seed=0,
            )
        return self._cached_data

    @property
    def name(self) -> str:
        return self._raw_json.get("name", "Real-World Benchmark Series")

    @property
    def version(self) -> str:
        data = self.load()
        return data.version

    @property
    def track(self) -> DatasetTrack:
        return DatasetTrack.TRACK_B_REAL

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
        return False

    @property
    def metadata(self) -> dict[str, Any]:
        self.load()
        return {
            "source": self._raw_json.get("source", "Empirical financial time series fixture"),
            "license": self._raw_json.get("license", "CC0 1.0 Universal"),
            "length": len(self._cached_data.returns) if self._cached_data else 0,
            "ground_truth_available": False,
            "label_quality": "Unlabeled empirical observations (no synthetic ground truth assumed)",
            "known_limitations": [
                "Real market returns contain unknown exogenous shocks, news flow, and microstructure noise.",
                "No true change-point dates can be claimed with 100% certainty.",
            ],
        }
