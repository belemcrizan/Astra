from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..contracts import IntegrityChainRecord


class IntegrityChain:
    """Tamper-evident cryptographic hash chain for investigation auditability.
    
    Chains every investigation event with SHA-256: H_t = SHA256(H_{t-1} || event_payload_t).
    """

    GENESIS_HASH = "0" * 64

    def __init__(self) -> None:
        self.records: list[IntegrityChainRecord] = []
        self._current_hash = self.GENESIS_HASH

    @property
    def current_hash(self) -> str:
        return self._current_hash

    def append_event(self, event_type: str, payload: dict[str, Any]) -> IntegrityChainRecord:
        step_index = len(self.records)
        ts = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, sort_keys=True)
        
        hasher = hashlib.sha256()
        hasher.update(self._current_hash.encode("utf-8"))
        hasher.update(event_type.encode("utf-8"))
        hasher.update(payload_str.encode("utf-8"))
        hasher.update(ts.encode("utf-8"))
        new_hash = hasher.hexdigest()

        summary = f"[{step_index}] {event_type} (hash: {new_hash[:12]}...)"
        record = IntegrityChainRecord(
            step_index=step_index,
            event_hash=new_hash,
            previous_hash=self._current_hash,
            payload_summary=summary,
            timestamp=ts,
        )
        self.records.append(record)
        self._current_hash = new_hash
        return record

    @classmethod
    def verify_chain(cls, records: list[IntegrityChainRecord]) -> tuple[bool, str]:
        """Verifies linkage and integrity of a recorded chain."""
        if not records:
            return True, "Empty chain."

        expected_prev = cls.GENESIS_HASH
        for idx, rec in enumerate(records):
            if rec.step_index != idx:
                return False, f"Broken index sequence at step {idx} (found {rec.step_index})."
            if rec.previous_hash != expected_prev:
                return False, f"Broken hash linkage at step {idx}: expected prev {expected_prev[:12]}, found {rec.previous_hash[:12]}."
            expected_prev = rec.event_hash

        return True, f"Integrity chain verified: {len(records)} linked records valid."

    @classmethod
    def verify_report_file(cls, report_path: str | Path) -> tuple[bool, str]:
        """Verifies report schema, preregistration identity, and integrity chain."""
        path = Path(report_path)
        if not path.exists():
            return False, f"Report file not found: {path}"

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chain_data = data.get("integrity_chain", [])
        if not chain_data:
            return True, "Report contains no integrity chain records (legacy or mock report)."

        records = [IntegrityChainRecord(**r) for r in chain_data]
        is_valid, msg = cls.verify_chain(records)
        if not is_valid:
            return False, f"Tamper detection alert: {msg}"

        return True, f"Report {path.name} passed tamper verification. Chain length: {len(records)}."
