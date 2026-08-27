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
    
    # ASTRA v0.3 Agent & Investigation Settings
    use_llm: bool = Field(default=False)
    gemini_api_key: str | None = None
    gemini_model: str = Field(default="gemini-2.5-flash")
    max_investigation_steps: int = Field(default=5, ge=1, le=20)
    max_investigation_tests: int = Field(default=6, ge=1, le=30)
    max_cost_units: float = Field(default=10.0, ge=1.0)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            seed=int(os.getenv("ASTRA_SEED", "42")),
            points=int(os.getenv("ASTRA_POINTS", "2400")),
            agent_timeout_seconds=float(os.getenv("ASTRA_AGENT_TIMEOUT_SECONDS", "1.5")),
            max_retries=int(os.getenv("ASTRA_MAX_RETRIES", "1")),
            min_evidence_score=float(os.getenv("ASTRA_MIN_EVIDENCE_SCORE", "0.60")),
            output_dir=Path(os.getenv("ASTRA_OUTPUT_DIR", "artifacts")),
            use_llm=os.getenv("ASTRA_USE_LLM", "false").lower() in ("true", "1", "yes"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            max_investigation_steps=int(os.getenv("ASTRA_MAX_STEPS", "5")),
            max_investigation_tests=int(os.getenv("ASTRA_MAX_TESTS", "6")),
            max_cost_units=float(os.getenv("ASTRA_MAX_COST_UNITS", "10.0")),
        )
