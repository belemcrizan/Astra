from __future__ import annotations

from typing import Any

from ..contracts import (
    ActionUtilityEstimate,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationHypothesis,
    StopReason,
)


class StoppingPolicy:
    """Formal Stopping Policy for ASTRA Investigations.
    
    Determines when acquiring further evidence is no longer justified, providing
    explicit, auditable stop reasons.
    """

    @classmethod
    def evaluate_stop(
        cls,
        ranked_hypotheses: list[InvestigationHypothesis],
        utility_estimates: list[ActionUtilityEstimate],
        budget: InvestigationBudget,
        unknown_score: float = 0.20,
        min_evidence_score: float = 0.60,
        voi_threshold: float = 0.05,
    ) -> tuple[bool, StopReason, str]:
        if not ranked_hypotheses:
            return True, StopReason.NO_VALID_ACTION, "No active hypotheses in pool."

        lead = ranked_hypotheses[0]
        second = ranked_hypotheses[1] if len(ranked_hypotheses) > 1 else ranked_hypotheses[0]
        score_gap = lead.evidence_score - second.evidence_score

        # 1. Budget limits
        if budget.is_exhausted():
            return True, StopReason.BUDGET_EXHAUSTED, f"Computational budget exhausted ({budget.cost_units_used:.1f}/{budget.max_cost_units} cost units, {budget.tests_used}/{budget.max_tests} tests)."

        # 2. Unknown-dominant regime
        if unknown_score >= 0.60 and lead.id == "H_unknown":
            return True, StopReason.UNKNOWN_DOMINANT, f"Unmodeled dynamics dominant (unknown score: {unknown_score:.2f}). Refusing forced classification."

        # 3. Conclusive decision sufficiency
        if lead.evidence_score >= 0.70 and score_gap >= 0.30:
            return True, StopReason.DECISION_SUFFICIENT, f"Conclusive differentiation: {lead.id} reached {lead.evidence_score:.0%} evidence score with {score_gap:.0%} margin over runner-up {second.id}."

        # 4. Information exhaustion (no viable actions left)
        if not utility_estimates:
            return True, StopReason.INFORMATION_EXHAUSTED, "All viable discriminative tests have been executed."

        # 5. Non-positive Value of Information (VoI <= 0)
        best_candidate = utility_estimates[0]
        if best_candidate.voi <= voi_threshold and budget.tests_used >= 2:
            return True, StopReason.EXPECTED_VOI_NON_POSITIVE, f"Top candidate test '{best_candidate.action.value}' has non-positive VoI ({best_candidate.voi:.2f} <= {voi_threshold:.2f}). Further investigation cost exceeds expected decision value."

        # Continue investigation
        return False, StopReason.DECISION_SUFFICIENT, "Investigation ongoing."
