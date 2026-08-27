from __future__ import annotations

from typing import Any
import numpy as np

from ..contracts import (
    Hypothesis,
    HypothesisStatus,
    InvestigationHypothesis,
)


class CompetingHypothesisPool:
    """Manages the pool of competing explanations for an observed anomaly in ASTRA v0.4.
    
    Includes functional open-set H_unknown scoring, hypothesis trap recovery,
    and structured falsification tracking.
    """

    def __init__(self) -> None:
        self.hypotheses: dict[str, InvestigationHypothesis] = self._init_default_pool()
        self.unknown_score: float = 0.20
        self.hypothesis_expansion_proposals: list[str] = []

    def _init_default_pool(self) -> dict[str, InvestigationHypothesis]:
        return {
            "H1": InvestigationHypothesis(
                id="H1",
                name="Transient Statistical Fluctuation",
                claim="Observed peak is an isolated random noise outlier with no structural or volatility shift.",
                prior_evidence_score=0.45,
                evidence_score=0.45,
                status=HypothesisStatus.LEADING,
            ),
            "H2": InvestigationHypothesis(
                id="H2",
                name="Gradual Regime Change",
                claim="Persistent transition in baseline mean return or variance clustering.",
                prior_evidence_score=0.40,
                evidence_score=0.40,
                status=HypothesisStatus.ACTIVE,
            ),
            "H3": InvestigationHypothesis(
                id="H3",
                name="Abrupt Structural Break",
                claim="Sharp, discrete change-point in underlying distribution parameters.",
                prior_evidence_score=0.35,
                evidence_score=0.35,
                status=HypothesisStatus.ACTIVE,
            ),
            "H4": InvestigationHypothesis(
                id="H4",
                name="Coordinated Weak Signal",
                claim="Structured, sub-threshold waveform aligned across known historical events.",
                prior_evidence_score=0.30,
                evidence_score=0.30,
                status=HypothesisStatus.ACTIVE,
            ),
            "H_unknown": InvestigationHypothesis(
                id="H_unknown",
                name="Unmodeled Exogenous Dynamics",
                claim="Complex dynamics outside standard parametric models.",
                prior_evidence_score=0.20,
                evidence_score=0.20,
                status=HypothesisStatus.ACTIVE,
            ),
        }

    def get_ranked_hypotheses(self) -> list[InvestigationHypothesis]:
        return sorted(self.hypotheses.values(), key=lambda h: h.evidence_score, reverse=True)

    def all(self) -> list[InvestigationHypothesis]:
        return self.get_ranked_hypotheses()

    def get_leading(self) -> InvestigationHypothesis:
        return self.get_ranked_hypotheses()[0]

    def update_evidence(
        self,
        test_name_or_hid: str | None = None,
        supports: list[str] | None = None,
        contradicts: list[str] | None = None,
        evidence_delta: float = 0.15,
        delta: float | None = None,
        supporting_msg: str = "",
        test_name: str = "",
    ) -> InvestigationHypothesis | None:
        # Check if called via legacy signature: pool.update_evidence("H3", delta=+0.35, ...)
        if delta is not None:
            hid = test_name_or_hid or "H3"
            if hid in self.hypotheses:
                h = self.hypotheses[hid]
                h.evidence_score = max(0.01, min(0.99, round(h.evidence_score + delta, 3)))
                if supporting_msg:
                    h.supporting_evidence.append(supporting_msg)
                if test_name:
                    h.tests_executed.append(test_name)
                self._update_statuses_and_unknown()
                return h
            return None

        # Standard signature
        tname = test_name_or_hid or test_name or "diagnostic_test"
        for hid in (supports or []):
            if hid in self.hypotheses:
                h = self.hypotheses[hid]
                h.evidence_score = min(0.99, round(h.evidence_score + evidence_delta, 3))
                h.supporting_evidence.append(tname)
                h.tests_executed.append(tname)
                if h.status == HypothesisStatus.CHALLENGED:
                    h.status = HypothesisStatus.ACTIVE

        for hid in (contradicts or []):
            if hid in self.hypotheses:
                h = self.hypotheses[hid]
                h.evidence_score = max(0.01, round(h.evidence_score - evidence_delta * 1.5, 3))
                h.contradicting_evidence.append(tname)
                h.falsification_attempts += 1
                h.tests_executed.append(tname)
                h.falsification_outcomes.append({
                    "test": tname,
                    "result": "contradicted",
                    "remaining_score": h.evidence_score,
                })
                if h.evidence_score <= 0.20:
                    h.status = HypothesisStatus.FALSIFIED
                else:
                    h.status = HypothesisStatus.CHALLENGED

        self._update_statuses_and_unknown()
        return self.get_leading()

    def record_falsification_attempt(
        self,
        hypothesis_id: str,
        test_name: str,
        falsified: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        if hypothesis_id in self.hypotheses:
            h = self.hypotheses[hypothesis_id]
            h.falsification_attempts += 1
            h.falsification_outcomes.append({
                "test": test_name,
                "falsified": falsified,
                "details": details or {},
            })
            if falsified:
                h.evidence_score = max(0.01, round(h.evidence_score - 0.25, 3))
                h.contradicting_evidence.append(f"Contradicted by {test_name}")
                if h.evidence_score <= 0.20:
                    h.status = HypothesisStatus.FALSIFIED
                else:
                    h.status = HypothesisStatus.CHALLENGED
            self._update_statuses_and_unknown()

    def get(self, hypothesis_id: str) -> InvestigationHypothesis | None:
        return self.hypotheses.get(hypothesis_id)

    def _update_statuses_and_unknown(self) -> None:
        # Re-rank
        ranked = self.get_ranked_hypotheses()
        if ranked and ranked[0].status not in (HypothesisStatus.FALSIFIED,):
            if ranked[0].evidence_score >= 0.70:
                ranked[0].status = HypothesisStatus.CONFIRMED
            else:
                ranked[0].status = HypothesisStatus.LEADING

        for h in self.hypotheses.values():
            if h != ranked[0] and h.status == HypothesisStatus.LEADING:
                h.status = HypothesisStatus.ACTIVE

        # Dynamic H_unknown scoring
        known = [h for h in self.hypotheses.values() if h.id != "H_unknown"]
        all_known_falsified = all(h.status == HypothesisStatus.FALSIFIED or h.evidence_score < 0.20 for h in known)

        if all_known_falsified:
            self.unknown_score = 0.85
            self.hypotheses["H_unknown"].evidence_score = 0.85
            self.hypotheses["H_unknown"].status = HypothesisStatus.CONFIRMED
            if "Unmodeled Exogenous Jump-Diffusion Dynamics" not in self.hypothesis_expansion_proposals:
                self.hypothesis_expansion_proposals.append("Unmodeled Exogenous Jump-Diffusion Dynamics")
        elif ranked and ranked[0].id == "H1" and ranked[0].evidence_score >= 0.40:
            # Benign noise survived; unmodeled dynamics are not dominant
            self.unknown_score = 0.15
            self.hypotheses["H_unknown"].evidence_score = 0.15
        elif ranked and ranked[0].evidence_score >= 0.50:
            self.unknown_score = round(max(0.10, 0.40 - ranked[0].evidence_score * 0.3), 3)
            self.hypotheses["H_unknown"].evidence_score = self.unknown_score
        else:
            self.unknown_score = 0.30
            self.hypotheses["H_unknown"].evidence_score = 0.30

    def to_legacy_hypotheses(self) -> list[Hypothesis]:
        return [
            Hypothesis(
                hypothesis_id=h.id,
                claim=h.claim,
                evidence_score=h.evidence_score,
                supporting_agents=h.supporting_evidence,
                required_evidence=["window_contrast", "segmentation_pelt"],
                falsification_status=h.status.value,
                counterevidence=h.contradicting_evidence,
            )
            for h in self.hypotheses.values()
        ]


# Backward compatibility aliases
HypothesisPool = CompetingHypothesisPool

def create_standard_hypothesis_pool() -> CompetingHypothesisPool:
    return CompetingHypothesisPool()
