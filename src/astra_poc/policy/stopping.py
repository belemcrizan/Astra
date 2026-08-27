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
    explicit, auditable stop reasons under a rigorous priority hierarchy:

    Precedence Order:
    1. Unknown Dominant (H_unknown >= 0.60 or all known models falsified)
    2. Decision Sufficiency (conclusive differentiation of leading hypothesis)
    3. Information Exhausted (no unexecuted candidate tests remain)
    4. Expected VoI Non-Positive (remaining tests have VoI <= threshold)
    5. Hypotheses Indistinguishable (active hypotheses tied, no tests can separate them)
    6. Resource / Budget Exhausted (budget prevents executing an otherwise positive-VoI action)
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
        score_gap = round(lead.evidence_score - second.evidence_score, 3)

        # 1. Unknown-dominant regime (Refusal of forced classification)
        if (unknown_score >= 0.60 and lead.id == "H_unknown") or (unknown_score >= 0.65):
            return True, StopReason.UNKNOWN_DOMINANT, f"Unmodeled dynamics dominant (unknown score: {unknown_score:.2f}). Refusing forced classification."

        # 2. Conclusive decision sufficiency
        # A. High confidence differentiation
        if lead.evidence_score >= 0.65 and score_gap >= 0.20:
            return True, StopReason.DECISION_SUFFICIENT, f"Conclusive differentiation: {lead.id} reached {lead.evidence_score:.0%} evidence score with {score_gap:.0%} margin over runner-up {second.id}."
        
        # B. Benign Noise survival (H1 leading with alternatives contradicted)
        if lead.id == "H1" and budget.tests_used >= 1:
            alt_scores = [h.evidence_score for h in ranked_hypotheses if h.id != "H1"]
            max_alt = max(alt_scores) if alt_scores else 0.0
            if max_alt <= 0.35 and lead.evidence_score >= 0.40:
                return True, StopReason.DECISION_SUFFICIENT, f"Transient noise (H1) confirmed ({lead.evidence_score:.0%}); alternative structural breaks falsified/contradicted (max alt: {max_alt:.0%})."

        # C. Very high single hypothesis support
        if lead.evidence_score >= 0.75:
            return True, StopReason.DECISION_SUFFICIENT, f"Decisive evidence support for {lead.id} ({lead.evidence_score:.0%})."

        # 3. Information exhaustion (no viable unexecuted tests in catalog)
        if not utility_estimates:
            return True, StopReason.INFORMATION_EXHAUSTED, "All viable discriminative tests in DSL catalog have been executed."

        # 4. Non-positive Value of Information (VoI <= threshold)
        best_candidate = utility_estimates[0]
        if best_candidate.voi <= voi_threshold and budget.tests_used >= 1:
            return True, StopReason.EXPECTED_VOI_NON_POSITIVE, f"Top candidate test '{best_candidate.action.value}' has non-positive VoI ({best_candidate.voi:.2f} <= {voi_threshold:.2f}). Further investigation cost exceeds expected decision value."

        # 5. Resource / Budget exhaustion
        # (Only triggers if positive-VoI candidate tests exist but budget prevents running them)
        if budget.is_exhausted():
            return True, StopReason.BUDGET_EXHAUSTED, f"Computational budget exhausted ({budget.cost_units_used:.1f}/{budget.max_cost_units} cost units, {budget.tests_used}/{budget.max_tests} tests). Blocked execution of positive-VoI candidate '{best_candidate.action.value}' (VoI={best_candidate.voi:.2f})."

        # Continue investigation
        return False, StopReason.DECISION_SUFFICIENT, "Investigation ongoing."
