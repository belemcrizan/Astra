from __future__ import annotations

from ..contracts import (
    DecisionOutcome,
    DecisionReasonCode,
    HypothesisStatus,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationHypothesis,
)
from ..hypotheses.pool import HypothesisPool


class DecisionPolicy:
    """Explicit decision policy engine for ASTRA investigations.
    
    Evaluates competing hypotheses, falsification outcomes, and resource budgets
    to produce machine-readable decisions and traceable reason codes.
    """

    @classmethod
    def evaluate(
        cls,
        pool: HypothesisPool,
        budget: InvestigationBudget,
        min_evidence_score: float = 0.60,
    ) -> DecisionOutcome:
        ranked = pool.all()
        if not ranked:
            return DecisionOutcome(
                decision=InvestigationDecision.DEFER,
                reason_codes=[DecisionReasonCode.BUDGET_EXHAUSTED],
                primary_reason="No hypotheses available in pool.",
                human_review_required=True,
            )

        lead: InvestigationHypothesis = ranked[0]
        second: InvestigationHypothesis = ranked[1] if len(ranked) > 1 else ranked[0]
        score_gap = lead.evidence_score - second.evidence_score
        residual_uncertainty = round(max(0.0, 1.0 - (score_gap + lead.evidence_score) / 2), 3)

        # Case 1: Budget exhausted before clear differentiation
        if budget.is_exhausted() and score_gap < 0.15 and lead.evidence_score < min_evidence_score:
            return DecisionOutcome(
                decision=InvestigationDecision.DEFER,
                reason_codes=[
                    DecisionReasonCode.BUDGET_EXHAUSTED,
                    DecisionReasonCode.MATERIAL_UNCERTAINTY,
                ],
                primary_reason=f"Investigation resource budget exhausted ({budget.cost_units_used:.1f}/{budget.max_cost_units} cost units) while top hypotheses ({lead.id} vs {second.id}) remained within {score_gap:.2f} score margin.",
                human_review_required=True,
                accepted_hypothesis_id=None,
                residual_uncertainty=residual_uncertainty,
            )

        # Case 2: Benign noise survives falsification (H1 confirmed or competitors falsified)
        if lead.id == "H1" and (lead.evidence_score >= min_evidence_score or second.status == HypothesisStatus.FALSIFIED):
            return DecisionOutcome(
                decision=InvestigationDecision.CLOSE,
                reason_codes=[
                    DecisionReasonCode.BENIGN_FLUCTUATION_SURVIVED,
                    DecisionReasonCode.TRANSIENT_NOISE_CONFIRMED,
                ],
                primary_reason=f"Transient statistical fluctuation hypothesis (H1) survived with evidence score {lead.evidence_score:.0%}. No persistent structural break confirmed.",
                human_review_required=False,
                accepted_hypothesis_id="H1",
                residual_uncertainty=residual_uncertainty,
            )

        # Case 3: Structural break confirmed (H3)
        if lead.id == "H3" and lead.evidence_score >= min_evidence_score:
            return DecisionOutcome(
                decision=InvestigationDecision.ESCALATE,
                reason_codes=[
                    DecisionReasonCode.STRUCTURAL_BREAK_SUPPORTED,
                    DecisionReasonCode.ALTERNATIVE_NOT_FALSIFIED,
                ],
                primary_reason=f"Abrupt structural break (H3) confirmed across optimal segmentation and change-point tests (score: {lead.evidence_score:.0%}).",
                human_review_required=True,
                accepted_hypothesis_id="H3",
                residual_uncertainty=residual_uncertainty,
            )

        # Case 4: Gradual regime change confirmed (H2)
        if lead.id == "H2" and lead.evidence_score >= min_evidence_score:
            return DecisionOutcome(
                decision=InvestigationDecision.ESCALATE,
                reason_codes=[
                    DecisionReasonCode.REGIME_SHIFT_CONFIRMED,
                    DecisionReasonCode.ALTERNATIVE_NOT_FALSIFIED,
                ],
                primary_reason=f"Gradual regime change (H2) confirmed across local variance contrast and susceptibility metrics (score: {lead.evidence_score:.0%}).",
                human_review_required=True,
                accepted_hypothesis_id="H2",
                residual_uncertainty=residual_uncertainty,
            )

        # Case 5: Coordinated weak signal confirmed (H4)
        if lead.id == "H4" and lead.evidence_score >= min_evidence_score:
            return DecisionOutcome(
                decision=InvestigationDecision.ESCALATE,
                reason_codes=[
                    DecisionReasonCode.COORDINATED_WEAK_SIGNAL_DETECTED,
                    DecisionReasonCode.ALTERNATIVE_NOT_FALSIFIED,
                ],
                primary_reason=f"Coordinated weak signal (H4) empirically separated from circular temporal null (score: {lead.evidence_score:.0%}).",
                human_review_required=True,
                accepted_hypothesis_id="H4",
                residual_uncertainty=residual_uncertainty,
            )

        # Case 6: Moderate evidence requiring monitoring (WATCH)
        if lead.evidence_score >= 0.40:
            return DecisionOutcome(
                decision=InvestigationDecision.WATCH,
                reason_codes=[
                    DecisionReasonCode.ALTERNATIVE_NOT_FALSIFIED,
                    DecisionReasonCode.MATERIAL_UNCERTAINTY,
                ],
                primary_reason=f"Emerging signal for {lead.id} ({lead.name}) with score {lead.evidence_score:.0%}; insufficient for immediate escalation but warrants ongoing observation.",
                human_review_required=False,
                accepted_hypothesis_id=lead.id,
                residual_uncertainty=residual_uncertainty,
            )

        # Default fallback
        return DecisionOutcome(
            decision=InvestigationDecision.WATCH,
            reason_codes=[DecisionReasonCode.MATERIAL_UNCERTAINTY],
            primary_reason="Evidence across all hypotheses remains inconclusive. Placing signal on watch status.",
            human_review_required=False,
            accepted_hypothesis_id=None,
            residual_uncertainty=residual_uncertainty,
        )
