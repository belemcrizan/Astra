from __future__ import annotations

import threading
from typing import Any
from uuid import uuid4

from ..contracts import InvestigationBudget
from .locks import OptimisticCaseLock


class CaseIsolationViolationError(Exception):
    """Raised when an operation attempts to cross case boundaries."""
    pass


class CaseContext:
    """Fortified isolation boundary for an individual investigation case."""

    def __init__(self, case_id: str, tenant_id: str = "default-tenant") -> None:
        self.case_id = case_id
        self.tenant_id = tenant_id
        self.budget = InvestigationBudget()
        self.evidence_ids: set[str] = set()
        self.version = 1
        self.lease_token: str | None = None
        self.is_active = True


class CaseIsolationManager:
    """Manages independent concurrent investigation cases without cross-case leakage."""

    _instance: CaseIsolationManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._cases: dict[str, CaseContext] = {}
        self._lock_manager = OptimisticCaseLock()

    @classmethod
    def get_instance(cls) -> CaseIsolationManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = CaseIsolationManager()
            return cls._instance

    def create_case(self, case_id: str | None = None, tenant_id: str = "default-tenant") -> CaseContext:
        cid = case_id or f"case-{uuid4().hex[:8]}"
        ctx = CaseContext(case_id=cid, tenant_id=tenant_id)
        token, ver = self._lock_manager.acquire_lease(cid)
        ctx.lease_token = token
        ctx.version = ver
        self._cases[cid] = ctx
        return ctx

    def get_case(self, case_id: str, requesting_tenant: str = "default-tenant") -> CaseContext:
        if case_id not in self._cases:
            raise CaseIsolationViolationError(f"Case '{case_id}' not found.")
        ctx = self._cases[case_id]
        if ctx.tenant_id != requesting_tenant:
            raise CaseIsolationViolationError(
                f"Unauthorized cross-tenant access: tenant '{requesting_tenant}' attempted to access case '{case_id}' owned by tenant '{ctx.tenant_id}'."
            )
        return ctx

    def mutate_case_version(self, case_id: str, expected_version: int, lease_token: str) -> int:
        ctx = self.get_case(case_id)
        new_ver = self._lock_manager.mutate_case(case_id, expected_version, lease_token)
        ctx.version = new_ver
        return new_ver

    def close_case(self, case_id: str) -> None:
        if case_id in self._cases:
            ctx = self._cases[case_id]
            if ctx.lease_token:
                self._lock_manager.release_lease(case_id, ctx.lease_token)
            ctx.is_active = False
