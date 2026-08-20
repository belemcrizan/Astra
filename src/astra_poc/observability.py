from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


class RunLogger:
    """Minimal JSON telemetry with IDs compatible with later OTel migration."""

    def __init__(self, run_id: str, correlation_id: str, output_dir: Path):
        self.run_id = run_id
        self.correlation_id = correlation_id
        self.path = output_dir / "runs" / f"{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **fields: object) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
            "event": event,
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    @contextmanager
    def span(self, agent_id: str) -> Iterator[None]:
        started = time.perf_counter()
        self.emit("agent_started", agent_id=agent_id)
        try:
            yield
        except Exception as exc:
            self.emit("agent_failed", agent_id=agent_id, error=type(exc).__name__)
            raise
        finally:
            self.emit("agent_finished", agent_id=agent_id, latency_ms=round((time.perf_counter() - started) * 1000, 3))

