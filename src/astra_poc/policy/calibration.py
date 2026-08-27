from __future__ import annotations

import math
from typing import Any


class CalibrationLayer:
    """Decision calibration and selective risk-coverage assessment.
    
    Translates raw heuristic evidence scores into calibrated decision confidence
    and enables selective decision refusal for enterprise safety governance.
    """

    @classmethod
    def calibrate_confidence(cls, evidence_score: float, temperature: float = 0.85) -> float:
        """Calibrates an uncalibrated score into a decision confidence metric in [0.0, 1.0]."""
        # Shifted sigmoid scaling
        logit = (evidence_score - 0.50) / max(temperature, 0.1)
        prob = 1.0 / (1.0 + math.exp(-logit * 3.0))
        return round(float(prob), 4)

    @classmethod
    def evaluate_selective_coverage(
        cls,
        confidence: float,
        tau_threshold: float = 0.65,
    ) -> tuple[bool, str]:
        """Evaluates whether autonomous resolution meets the selective confidence threshold tau."""
        if confidence >= tau_threshold:
            return True, f"Decision confidence {confidence:.1%} meets selective autonomy threshold {tau_threshold:.1%}."
        return False, f"Decision confidence {confidence:.1%} is below selective threshold {tau_threshold:.1%}. Deferring to human operator."

    @classmethod
    def compute_risk_coverage_curve(
        cls,
        predictions: list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Generates empirical Risk vs Coverage coordinates across tau thresholds."""
        thresholds = [0.50, 0.60, 0.70, 0.80, 0.90, 0.95]
        curve = []
        n = max(len(predictions), 1)

        for tau in thresholds:
            covered = [p for p in predictions if p.get("confidence", 0.0) >= tau]
            coverage = len(covered) / n
            if covered:
                errors = sum(int(p.get("is_error", False)) for p in covered)
                risk = errors / len(covered)
            else:
                risk = 0.0

            curve.append({
                "tau": tau,
                "coverage": round(coverage, 3),
                "risk": round(risk, 3),
                "retained_count": len(covered),
            })

        return curve
