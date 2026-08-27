from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..contracts import DSLOperation, DSLOperationName, InvestigationBudget
from .dsl import DSL_OPERATION_SPECS, DSLOperationSpec

# Adversarial injection patterns
FORBIDDEN_PATTERNS = [
    r"__",
    r"import\s+",
    r"eval\(",
    r"exec\(",
    r"system\(",
    r"subprocess",
    r"open\(",
    r"os\.",
    r"sys\.",
    r"lambda",
    r";",
    r"\n",
]
FORBIDDEN_REGEX = re.compile("|".join(FORBIDDEN_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    error: str | None = None
    sanitized_operation: DSLOperation | None = None


class DSLValidator:
    """Deterministic validator and security sandbox gate for ASTRA DSL operations.
    
    Rejects:
    - Unknown operations
    - Malformed argument dictionaries
    - Out-of-range parameters
    - Type mismatches
    - Injection strings or code execution tokens
    - Resource / budget limit violations
    """

    @classmethod
    def validate(
        cls,
        operation: DSLOperation,
        budget: InvestigationBudget | None = None,
    ) -> ValidationResult:
        # 1. Operation name check
        if operation.op_name not in DSL_OPERATION_SPECS:
            return ValidationResult(
                is_valid=False,
                error=f"Unauthorized or unknown operation: '{operation.op_name}'. Allowed: {[op.value for op in DSL_OPERATION_SPECS]}",
            )

        spec: DSLOperationSpec = DSL_OPERATION_SPECS[operation.op_name]

        # 2. Budget constraint check
        if budget is not None:
            if budget.tests_used + 1 > budget.max_tests:
                return ValidationResult(
                    is_valid=False,
                    error=f"Budget exceeded: max tests limit reached ({budget.tests_used}/{budget.max_tests})",
                )
            if budget.cost_units_used + spec.cost_units > budget.max_cost_units:
                return ValidationResult(
                    is_valid=False,
                    error=f"Budget exceeded: max cost units limit reached ({budget.cost_units_used + spec.cost_units:.2f}/{budget.max_cost_units:.2f})",
                )

        args = operation.args or {}
        sanitized_args: dict[str, Any] = {}

        # 3. Disallow unexpected arguments
        for arg_name, arg_val in args.items():
            if arg_name not in spec.params:
                return ValidationResult(
                    is_valid=False,
                    error=f"Unexpected parameter '{arg_name}' for operation '{operation.op_name}'. Allowed: {list(spec.params.keys())}",
                )

            # Security string check against injection
            if isinstance(arg_val, str) and FORBIDDEN_REGEX.search(arg_val):
                return ValidationResult(
                    is_valid=False,
                    error=f"Security violation: forbidden token detected in argument '{arg_name}': '{arg_val}'",
                )

        # 4. Validate defined parameters
        for param_name, param_spec in spec.params.items():
            val = args.get(param_name)

            if val is None:
                if param_spec.required:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Missing required parameter '{param_name}' for operation '{operation.op_name}'",
                    )
                sanitized_args[param_name] = param_spec.default
                continue

            # Type and range checking
            if param_spec.type_name in ("float", "int"):
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    return ValidationResult(
                        is_valid=False,
                        error=f"Parameter '{param_name}' must be numeric ({param_spec.type_name}), got {type(val).__name__}",
                    )
                num_val = float(val) if param_spec.type_name == "float" else int(val)
                if param_spec.min_value is not None and num_val < param_spec.min_value:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Parameter '{param_name}' value {num_val} is below minimum allowed {param_spec.min_value}",
                    )
                if param_spec.max_value is not None and num_val > param_spec.max_value:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Parameter '{param_name}' value {num_val} exceeds maximum allowed {param_spec.max_value}",
                    )
                sanitized_args[param_name] = num_val

            elif param_spec.type_name == "str":
                if not isinstance(val, str):
                    return ValidationResult(
                        is_valid=False,
                        error=f"Parameter '{param_name}' must be string, got {type(val).__name__}",
                    )
                if param_spec.allowed_values and val not in param_spec.allowed_values:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Parameter '{param_name}' value '{val}' not in allowed options: {param_spec.allowed_values}",
                    )
                sanitized_args[param_name] = val

            elif param_spec.type_name == "bool":
                if not isinstance(val, bool):
                    return ValidationResult(
                        is_valid=False,
                        error=f"Parameter '{param_name}' must be boolean, got {type(val).__name__}",
                    )
                sanitized_args[param_name] = val

        sanitized_op = DSLOperation(
            op_name=operation.op_name,
            args=sanitized_args,
            target_hypotheses=operation.target_hypotheses or spec.discriminates,
            cost_units=spec.cost_units,
            expected_info_value=operation.expected_info_value,
            reasoning=operation.reasoning,
        )

        return ValidationResult(is_valid=True, sanitized_operation=sanitized_op)
