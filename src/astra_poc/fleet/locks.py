from __future__ import annotations

import threading
import time
from uuid import uuid4


class StaleStateVersionError(Exception):
    """Raised when an operation attempts to mutate a case with an outdated version."""
    pass


class OptimisticCaseLock:
    """Provides optimistic concurrency control and lease tokens for case execution."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._versions: dict[str, int] = {}
        self._leases: dict[str, tuple[str, float]] = {}  # case_id -> (token, expiry)

    def acquire_lease(self, case_id: str, ttl_seconds: float = 30.0) -> tuple[str, int]:
        with self._lock:
            now = time.time()
            current_lease = self._leases.get(case_id)
            if current_lease and current_lease[1] > now:
                # Active lease exists
                token, _ = current_lease
                return token, self._versions.get(case_id, 1)

            new_token = f"lease-{uuid4().hex[:12]}"
            version = self._versions.get(case_id, 1)
            self._leases[case_id] = (new_token, now + ttl_seconds)
            self._versions[case_id] = version
            return new_token, version

    def mutate_case(self, case_id: str, expected_version: int, lease_token: str) -> int:
        with self._lock:
            current_version = self._versions.get(case_id, 1)
            if expected_version != current_version:
                raise StaleStateVersionError(
                    f"Stale state mutation on case '{case_id}': expected version {expected_version}, but current version is {current_version}."
                )

            current_lease = self._leases.get(case_id)
            if not current_lease or current_lease[0] != lease_token:
                raise StaleStateVersionError(
                    f"Invalid or expired lease token for case '{case_id}'."
                )

            new_version = current_version + 1
            self._versions[case_id] = new_version
            return new_version

    def release_lease(self, case_id: str, lease_token: str) -> None:
        with self._lock:
            current_lease = self._leases.get(case_id)
            if current_lease and current_lease[0] == lease_token:
                self._leases.pop(case_id, None)
