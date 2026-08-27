from __future__ import annotations

import unittest
from pydantic import ValidationError

from astra_poc.contracts import DSLOperation, DSLOperationName, InvestigationBudget
from astra_poc.datasets import generate_synthetic_market
from astra_poc.execution.executor import DSLExecutor
from astra_poc.execution.validator import DSLValidator


class DSLAndSecurityTests(unittest.TestCase):
    def test_valid_operation_passes_validation(self):
        op = DSLOperation(
            op_name=DSLOperationName.RUN_CUSUM,
            args={"drift": 0.10, "threshold": 12.0, "cooldown": 120},
        )
        res = DSLValidator.validate(op)
        self.assertTrue(res.is_valid)
        self.assertIsNotNone(res.sanitized_operation)

    def test_unknown_operation_rejected(self):
        with self.assertRaises(ValidationError):
            DSLOperation.model_validate({
                "op_name": "RUN_ARBITRARY_PYTHON",
                "args": {"code": "print(1)"},
            })

    def test_code_injection_in_arguments_rejected(self):
        malicious_op = DSLOperation(
            op_name=DSLOperationName.RUN_CUSUM,
            args={"drift": 0.10, "threshold": 12.0, "unexpected": "__import__('os').system('ls')"},
        )
        res = DSLValidator.validate(malicious_op)
        self.assertFalse(res.is_valid)

    def test_parameter_out_of_bounds_rejected(self):
        oob_op = DSLOperation(
            op_name=DSLOperationName.RUN_PELT,
            args={"minimum_segment": -10, "bic_multiplier": 3.0},
        )
        res = DSLValidator.validate(oob_op)
        self.assertFalse(res.is_valid)
        self.assertIn("below minimum allowed", res.error)

    def test_budget_exhaustion_rejected(self):
        budget = InvestigationBudget(max_cost_units=5.0, cost_units_used=4.5)
        op = DSLOperation(op_name=DSLOperationName.RUN_PELT)  # cost is 2.0
        res = DSLValidator.validate(op, budget=budget)
        self.assertFalse(res.is_valid)
        self.assertIn("Budget exceeded", res.error)

    def test_dsl_executor_executes_sandboxed_operations(self):
        data = generate_synthetic_market(1200, 42)
        executor = DSLExecutor(data)
        op = DSLOperation(op_name=DSLOperationName.RUN_PELT, args={"minimum_segment": 80, "bic_multiplier": 3.0})
        res = executor.execute(op)
        self.assertEqual(res.status, "success")
        self.assertTrue(len(res.evidence_generated) > 0)
        self.assertGreater(res.latency_ms, 0)


if __name__ == "__main__":
    unittest.main()
