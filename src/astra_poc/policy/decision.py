from __future__ import annotations

from typing import Any

from ..contracts import (
    DecisionOutcome,
    DecisionReasonCode,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationHypothesis,
    StopReason,
)
from .calibration import CalibrationLayer
from .recoverability import ActionRecoverabilityModel, DecisionCostModel


class InvestigationPolicy:
    """Unified Consequence-Aware Decision Policy for ASTRA v0.4.
    
    Evaluates competing hypotheses, unknown scores, recoverability, and calibration
    to determine the final investigation outcome.
    """

    def __init__(
        self,
        min_evidence_score: float = 0.60,
        margin_threshold: float = 0.20,
        unknown_threshold: float = 0.60,
        selective_tau: float = 0.65,
        cost_model: DecisionCostModel | None = None,
    ) -> None:
        self.min_evidence_score = min_evidence_score
        self.margin_threshold = margin_threshold
        self.unknown_threshold = unknown_threshold
        self.selective_tau = selective_tau
        self.cost_model = cost_model or DecisionCostModel()

    def evaluate(
        self,
        hypotheses: list[InvestigationHypothesis],
        budget: InvestigationBudget,
        unknown_score: float = 0.20,
        stop_reason: StopReason = StopReason.DECISION_SUFFICIENT,
        evidence_items_count: int = 0,
    ) -> DecisionOutcome:
        if not hypotheses:
            return DecisionOutcome(
                decision=InvestigationDecision.REQUEST_HUMAN_REVIEW,
                reason_codes=[DecisionReasonCode.MATERIAL_UNCERTAINTY],
                primary_reason="No hypotheses present in investigation context.",
                stop_reason=stop_reason,
                human_review_required=True,
                residual_uncertainty=1.0,
                decision_confidence=0.0,
                selective_decision_approved=False,
            )

        ranked = sorted(hypotheses, key=lambda h: h.evidence_score, reverse=True)
        leading = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None
        margin = (leading.evidence_score - runner_up.evidence_score) if runner_up else 1.0

        # Calibrate decision confidence
        confidence = CalibrationLayer.calibrate_confidence(leading.evidence_score)
        selective_approved, selective_reason = CalibrationLayer.evaluate_selective_coverage(
            confidence, tau_threshold=self.selective_tau
        )

        # 1. Open-Set / Unknown Dominance
        if unknown_score >= self.unknown_threshold or (leading.id == "H_unknown" and leading.evidence_score >= 0.50):
            return DecisionOutcome(
                decision=InvestigationDecision.DEFER,
                reason_codes=[DecisionReasonCode.UNKNOWN_REGIME_DOMINANT],
                primary_reason=f"Open-set dynamics dominant (unknown score: {unknown_score:.2f}). Refusing forced classification into known hypotheses.",
                stop_reason=StopReason.UNKNOWN_DOMINANT,
                human_review_required=True,
                accepted_hypothesis_id=leading.id,
                residual_uncertainty=round(1.0 - confidence, 3),
                decision_confidence=confidence,
                selective_decision_approved=False,
            )

        # 2. Budget Exhaustion with High Uncertainty
        if budget.is_exhausted() and (leading.evidence_score < self.min_evidence_score or margin < self.margin_threshold):
            if leading.id == "H1" and leading.evidence_score >= 0.40:
                return DecisionOutcome(
                    decision=InvestigationDecision.CLOSE,
                    reason_codes=[DecisionReasonCode.BENIGN_FLUCTUATION_SURVIVED, DecisionReasonCode.BUDGET_EXHAUSTED],
                    primary_reason=f"Budget exhausted after diagnostic tests; H1 (Transient Noise) remained leading with no confirmed structural shift. Safely closed.",
                    stop_reason=StopReason.BUDGET_EXHAUSTED,
                    human_review_required=False,
                    accepted_hypothesis_id="H1",
                    residual_uncertainty=round(1.0 - confidence, 3),
                    decision_confidence=confidence,
                    selective_decision_approved=selective_approved,
                )
            return DecisionOutcome(
                decision=InvestigationDecision.DEFER,
                reason_codes=[DecisionReasonCode.BUDGET_EXHAUSTED, DecisionReasonCode.MATERIAL_UNCERTAINTY],
                primary_reason=f"Budget exhausted ({budget.cost_units_used:.1f}/{budget.max_cost_units} cost units) with top contenders ({leading.id} vs {runner_up.id if runner_up else 'N/A'}) within {margin:.2f} score margin.",
                stop_reason=StopReason.BUDGET_EXHAUSTED,
                human_review_required=True,
                accepted_hypothesis_id=leading.id,
                residual_uncertainty=round(1.0 - confidence, 3),
                decision_confidence=confidence,
                selective_decision_approved=False,
            )

        # 3. Benign Noise Closure (H1 Survived Falsification)
        if leading.id == "H1" and leading.evidence_score >= self.min_evidence_score and margin >= self.margin_threshold:
            return DecisionOutcome(
                decision=InvestigationDecision.CLOSE,
                reason_codes=[DecisionReasonCode.BENIGN_FLUCTUATION_SURVIVED, DecisionReasonCode.TRANSIENT_NOISE_CONFIRMED],
                primary_reason=f"Transient statistical fluctuation (H1) confirmed ({leading.evidence_score:.0%} evidence). Routine noise closed safely.",
                stop_reason=stop_reason,
                human_review_required=False,
                accepted_hypothesis_id="H1",
                residual_uncertainty=round(1.0 - confidence, 3),
                decision_confidence=confidence,
                selective_decision_approved=selective_approved,
            )

        # 4. Material Escalation (H2, H3, H4 Confirmed)
        if leading.id in ("H2", "H3", "H4") and leading.evidence_score >= self.min_evidence_score:
            reason_map = {
                "H2": DecisionReasonCode.REGIME_SHIFT_CONFIRMED,
                "H3": DecisionReasonCode.STRUCTURAL_BREAK_SUPPORTED,
                "H4": DecisionReasonCode.COORDINATED_WEAK_SIGNAL_DETECTED,
            }
            code = reason_map.get(leading.id, DecisionReasonCode.REGIME_SHIFT_CONFIRMED)
            return DecisionOutcome(
                decision=InvestigationDecision.ESCALATE,
                reason_codes=[code],
                primary_reason=f"{leading.name} ({leading.id}) supported by discriminative evidence (score: {leading.evidence_score:.0%}).",
                stop_reason=stop_reason,
                human_review_required=True,
                accepted_hypothesis_id=leading.id,
                residual_uncertainty=round(1.0 - confidence, 3),
                decision_confidence=confidence,
                selective_decision_approved=selective_approved,
            )

        # 5. Intermediate Watching (Moderate drift)
        if leading.evidence_score >= 0.40:
            return DecisionOutcome(
                decision=InvestigationDecision.WATCH,
                reason_codes=[DecisionReasonCode.ALTERNATIVE_NOT_FALSIFIED],
                primary_reason=f"Leading hypothesis {leading.id} has moderate support ({leading.evidence_score:.0%}) but insufficient certainty for escalation.",
                stop_reason=stop_reason,
                human_review_required=False,
                accepted_hypothesis_id=leading.id,
                residual_uncertainty=round(1.0 - confidence, 3),
                decision_confidence=confidence,
                selective_decision_approved=selective_approved,
            )

        # 6. Default Safe Fallback: Human Review
        return DecisionOutcome(
            decision=InvestigationDecision.REQUEST_HUMAN_REVIEW,
            reason_codes=[DecisionReasonCode.MATERIAL_UNCERTAINTY],
            primary_reason="Investigation concluded with inconclusive evidence across all hypotheses.",
            stop_reason=stop_reason,
            human_review_required=True,
            accepted_hypothesis_id=leading.id,
            residual_uncertainty=round(1.0 - confidence, 3),
            decision_confidence=confidence,
            selective_decision_approved=False,
        )
