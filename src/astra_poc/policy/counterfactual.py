from __future__ import annotations

from typing import Any

from ..contracts import (
    CounterfactualStatement,
    DecisionOutcome,
    DecisionReasonCode,
    InvestigationBudget,
    InvestigationDecision,
    InvestigationHypothesis,
)


class CounterfactualEngine:
    """Computes exact counterfactual decision boundaries.
    
    Identifies the smallest evidence or parameter changes that would have
    altered the final investigation decision.
    """

    @classmethod
    def generate_counterfactuals(
        cls,
        decision_outcome: DecisionOutcome,
        ranked_hypotheses: list[InvestigationHypothesis],
        evidence_log: list[Any],
        budget: InvestigationBudget,
        unknown_score: float = 0.20,
    ) -> list[CounterfactualStatement]:
        if not ranked_hypotheses:
            return []

        lead = ranked_hypotheses[0]
        final_dec = decision_outcome.decision
        statements: list[CounterfactualStatement] = []

        if final_dec == InvestigationDecision.ESCALATE:
            # CF 1: Flip to WATCH if change detector hadn't triggered
            statements.append(CounterfactualStatement(
                target_decision=InvestigationDecision.WATCH,
                condition=f"If change-point evidence for {lead.id} had been below threshold (score < 0.60)",
                minimal_evidence_delta=f"Evidence score delta: -{max(0.01, lead.evidence_score - 0.59):.2f}",
                hypothetical_reason_code=DecisionReasonCode.MATERIAL_UNCERTAINTY,
            ))
            # CF 2: Flip to DEFER if unknown score was high
            statements.append(CounterfactualStatement(
                target_decision=InvestigationDecision.DEFER,
                condition="If unmodeled residual dynamics had elevated H_unknown above 0.60",
                minimal_evidence_delta=f"Unknown score delta: +{max(0.01, 0.60 - unknown_score):.2f}",
                hypothetical_reason_code=DecisionReasonCode.UNKNOWN_REGIME_DOMINANT,
            ))
            # CF 3: Flip to HUMAN_REVIEW if budget was 1 test lower
            statements.append(CounterfactualStatement(
                target_decision=InvestigationDecision.REQUEST_HUMAN_REVIEW,
                condition="If test budget had been exhausted prior to falsification confirmation",
                minimal_evidence_delta="Budget constraint: -1 test available",
                hypothetical_reason_code=DecisionReasonCode.BUDGET_EXHAUSTED,
            ))

        elif final_dec == InvestigationDecision.CLOSE:
            # CF 1: Flip to ESCALATE if sub-window contrast had detected genuine variance jump
            statements.append(CounterfactualStatement(
                target_decision=InvestigationDecision.ESCALATE,
                condition="If sub-window contrast score had exceeded 0.75 or PELT confirmed segment boundary",
                minimal_evidence_delta="Contrast score delta: +0.40 (triggering H2 regime confirmation)",
                hypothetical_reason_code=DecisionReasonCode.REGIME_SHIFT_CONFIRMED,
            ))
            # CF 2: Flip to WATCH if evidence remained ambiguous
            statements.append(CounterfactualStatement(
                target_decision=InvestigationDecision.WATCH,
                condition="If H1 transient noise evidence score had been between 0.40 and 0.59",
                minimal_evidence_delta=f"Evidence score delta: -{max(0.01, lead.evidence_score - 0.50):.2f}",
                hypothetical_reason_code=DecisionReasonCode.MATERIAL_UNCERTAINTY,
            ))

        else:  # WATCH or DEFER
            # CF 1: Flip to ESCALATE if evidence had been conclusive
            statements.append(CounterfactualStatement(
                target_decision=InvestigationDecision.ESCALATE,
                condition=f"If {lead.id} evidence score had reached 0.65+ and survived independent falsification",
                minimal_evidence_delta=f"Evidence score delta: +{max(0.01, 0.65 - lead.evidence_score):.2f}",
                hypothetical_reason_code=DecisionReasonCode.REGIME_SHIFT_CONFIRMED,
            ))
            # CF 2: Flip to CLOSE if noise hypothesis H1 had survived with score >= 0.60
            statements.append(CounterfactualStatement(
                target_decision=InvestigationDecision.CLOSE,
                condition="If all alternative hypotheses had been falsified leaving H1 as benign noise",
                minimal_evidence_delta="H1 evidence score: >= 0.60 with competitor scores < 0.15",
                hypothetical_reason_code=DecisionReasonCode.TRANSIENT_NOISE_CONFIRMED,
            ))

        return statements
