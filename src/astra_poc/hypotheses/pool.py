from __future__ import annotations

import copy
from typing import Any

from ..contracts import Hypothesis, HypothesisStatus, InvestigationHypothesis


def create_standard_hypothesis_pool() -> list[InvestigationHypothesis]:
    """Generates the standard competing hypotheses for ASTRA v0.3."""
    return [
        InvestigationHypothesis(
            id="H1",
            name="Transient Statistical Fluctuation",
            claim="The observed anomaly represents a transient sampling outlier with no persistent structural or volatility change.",
            prior_evidence_score=0.45,
            evidence_score=0.45,
            status=HypothesisStatus.ACTIVE,
            supporting_evidence=[],
            contradicting_evidence=[],
        ),
        InvestigationHypothesis(
            id="H2",
            name="Gradual Regime Change",
            claim="The series exhibits a gradual, persistent transition in mean return or volatility structure.",
            prior_evidence_score=0.40,
            evidence_score=0.40,
            status=HypothesisStatus.ACTIVE,
            supporting_evidence=[],
            contradicting_evidence=[],
        ),
        InvestigationHypothesis(
            id="H3",
            name="Abrupt Structural Break",
            claim="A sharp, discrete change-point occurred in the underlying distribution parameters.",
            prior_evidence_score=0.35,
            evidence_score=0.35,
            status=HypothesisStatus.ACTIVE,
            supporting_evidence=[],
            contradicting_evidence=[],
        ),
        InvestigationHypothesis(
            id="H4",
            name="Coordinated Weak Signal",
            claim="Events precede a structured, repeated weak response waveform detectable via temporal alignment.",
            prior_evidence_score=0.30,
            evidence_score=0.30,
            status=HypothesisStatus.ACTIVE,
            supporting_evidence=[],
            contradicting_evidence=[],
        ),
        InvestigationHypothesis(
            id="H_unknown",
            name="Unmodeled / Exogenous Anomaly",
            claim="The dynamics stem from complex or external factors not adequately captured by existing parametric models.",
            prior_evidence_score=0.20,
            evidence_score=0.20,
            status=HypothesisStatus.ACTIVE,
            supporting_evidence=[],
            contradicting_evidence=[],
        ),
    ]


class HypothesisPool:
    """Manages competing hypotheses during an investigation."""

    def __init__(self, hypotheses: list[InvestigationHypothesis] | None = None):
        self._hypotheses: dict[str, InvestigationHypothesis] = {
            h.id: copy.deepcopy(h) for h in (hypotheses or create_standard_hypothesis_pool())
        }

    def get(self, hypothesis_id: str) -> InvestigationHypothesis | None:
        return self._hypotheses.get(hypothesis_id)

    def all(self) -> list[InvestigationHypothesis]:
        return sorted(self._hypotheses.values(), key=lambda h: h.evidence_score, reverse=True)

    def get_leading(self) -> InvestigationHypothesis:
        return max(self._hypotheses.values(), key=lambda h: h.evidence_score)

    def update_evidence(
        self,
        hypothesis_id: str,
        delta: float,
        supporting_msg: str | None = None,
        contradicting_msg: str | None = None,
        test_name: str | None = None,
    ) -> InvestigationHypothesis:
        h = self._hypotheses[hypothesis_id]
        new_score = max(0.01, min(0.99, h.evidence_score + delta))
        h.evidence_score = round(new_score, 4)
        if supporting_msg and supporting_msg not in h.supporting_evidence:
            h.supporting_evidence.append(supporting_msg)
        if contradicting_msg and contradicting_msg not in h.contradicting_evidence:
            h.contradicting_evidence.append(contradicting_msg)
        if test_name and test_name not in h.tests_executed:
            h.tests_executed.append(test_name)

        # Update status based on score and contradiction
        if h.evidence_score < 0.15:
            h.status = HypothesisStatus.FALSIFIED
        elif h.contradicting_evidence and not h.supporting_evidence:
            h.status = HypothesisStatus.CHALLENGED
        elif h.evidence_score >= 0.70:
            h.status = HypothesisStatus.CONFIRMED
        else:
            h.status = HypothesisStatus.ACTIVE

        return h

    def record_falsification_attempt(
        self,
        hypothesis_id: str,
        test_name: str,
        falsified: bool,
        details: dict[str, Any],
    ) -> None:
        h = self._hypotheses[hypothesis_id]
        h.falsification_attempts += 1
        h.falsification_outcomes.append({
            "test_name": test_name,
            "falsified": falsified,
            "details": details,
        })
        if falsified:
            h.status = HypothesisStatus.FALSIFIED
            self.update_evidence(
                hypothesis_id,
                delta=-0.35,
                contradicting_msg=f"Falsification test '{test_name}' rejected expected hypothesis signature.",
                test_name=test_name,
            )
        else:
            self.update_evidence(
                hypothesis_id,
                delta=+0.15,
                supporting_msg=f"Survived falsification test '{test_name}'.",
                test_name=test_name,
            )

    def to_legacy_hypotheses(self) -> list[Hypothesis]:
        legacy = []
        for h in self.all():
            status = "passed" if h.status in (HypothesisStatus.CONFIRMED, HypothesisStatus.ACTIVE) and not h.contradicting_evidence else "challenged"
            legacy.append(Hypothesis(
                hypothesis_id=h.id,
                claim=h.claim,
                evidence_score=h.evidence_score,
                supporting_agents=h.supporting_evidence,
                required_evidence=[f"Test: {t}" for t in h.tests_executed] or ["baseline verification"],
                falsification_status=status,
                counterevidence=h.contradicting_evidence,
            ))
        return legacy
