from __future__ import annotations

from dataclasses import dataclass
from ..contracts import InvestigationDecision


@dataclass(frozen=True)
class DecisionCostModel:
    """Configurable consequence-aware decision cost assumptions."""
    false_close_cost: float = 10.0
    false_watch_cost: float = 3.0
    unnecessary_escalate_cost: float = 2.0
    unnecessary_defer_cost: float = 1.5


@dataclass(frozen=True)
class ActionRecoverabilityModel:
    """Abstracts decision irreversibility and operational operational risk."""
    
    @classmethod
    def get_recoverability_penalty(cls, decision: InvestigationDecision) -> float:
        """Returns risk penalty R(a) in [0.0, 1.0]. Lower = more easily reversed."""
        penalties = {
            InvestigationDecision.WATCH: 0.10,       # Highly recoverable: continuous monitoring
            InvestigationDecision.DEFER: 0.15,       # Highly recoverable: deferred for budget/operator
            InvestigationDecision.REQUEST_HUMAN_REVIEW: 0.25, # Operator time cost
            InvestigationDecision.ESCALATE: 0.40,    # Review cost & alert routing
            InvestigationDecision.CLOSE: 0.85,       # Irreversible: missed event if closed incorrectly
        }
        return penalties.get(decision, 0.50)
