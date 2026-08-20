from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    seed: int = Field(default=42, ge=0)
    points: int = Field(default=2400, ge=600, le=100_000)
    agent_timeout_seconds: float = Field(default=1.5, gt=0, le=30)
    max_retries: int = Field(default=1, ge=0, le=3)
    min_evidence_score: float = Field(default=0.60, ge=0, le=1)
    output_dir: Path = Path("artifacts")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            seed=int(os.getenv("ASTRA_SEED", "42")),
            points=int(os.getenv("ASTRA_POINTS", "2400")),
            agent_timeout_seconds=float(os.getenv("ASTRA_AGENT_TIMEOUT_SECONDS", "1.5")),
            max_retries=int(os.getenv("ASTRA_MAX_RETRIES", "1")),
            min_evidence_score=float(os.getenv("ASTRA_MIN_EVIDENCE_SCORE", "0.60")),
            output_dir=Path(os.getenv("ASTRA_OUTPUT_DIR", "artifacts")),
        )
