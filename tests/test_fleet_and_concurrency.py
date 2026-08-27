from __future__ import annotations

import unittest
from astra_poc.fleet.isolation import CaseIsolationManager, CaseIsolationViolationError
from astra_poc.fleet.locks import OptimisticCaseLock, StaleStateVersionError


class FleetAndConcurrencyTests(unittest.TestCase):
    def test_case_isolation_prevents_cross_tenant_access(self):
        manager = CaseIsolationManager()
        case_a = manager.create_case(case_id="case-101", tenant_id="tenant-alpha")
        case_b = manager.create_case(case_id="case-202", tenant_id="tenant-beta")

        # Alpha can access case-101
        self.assertEqual(manager.get_case("case-101", requesting_tenant="tenant-alpha").case_id, "case-101")

        # Beta cannot access case-101
        with self.assertRaises(CaseIsolationViolationError):
            manager.get_case("case-101", requesting_tenant="tenant-beta")

    def test_optimistic_lock_prevents_stale_mutations(self):
        lock_mgr = OptimisticCaseLock()
        token, ver = lock_mgr.acquire_lease("case-303")
        self.assertEqual(ver, 1)

        # First mutation succeeds and increments version to 2
        new_ver = lock_mgr.mutate_case("case-303", expected_version=1, lease_token=token)
        self.assertEqual(new_ver, 2)

        # Stale mutation with expected_version=1 must fail
        with self.assertRaises(StaleStateVersionError):
            lock_mgr.mutate_case("case-303", expected_version=1, lease_token=token)


if __name__ == "__main__":
    unittest.main()
