from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any


class DatasetTrack(StrEnum):
    TRACK_A_SYNTHETIC = "Track A (Controlled Synthetic)"
    TRACK_B_REAL = "Track B (Real Dataset)"


class DatasetAdapter(ABC):
    """Abstract base class for dataset adapters in ASTRA v0.3."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def track(self) -> DatasetTrack: ...

    @property
    @abstractmethod
    def watermark(self) -> str: ...

    @property
    @abstractmethod
    def sha256(self) -> str: ...

    @property
    @abstractmethod
    def has_ground_truth(self) -> bool: ...

    @property
    @abstractmethod
    def metadata(self) -> dict[str, Any]: ...

    @abstractmethod
    def load(self) -> Any: ...
