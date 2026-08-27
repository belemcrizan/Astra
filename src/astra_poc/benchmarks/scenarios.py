from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from ..contracts import InvestigationDecision


@dataclass
class BenchmarkScenario:
    scenario_id: str
    family: str  # A..J
    name: str
    description: str
    returns: np.ndarray
    price: np.ndarray
    volume: np.ndarray
    time: np.ndarray
    expected_decision: InvestigationDecision
    acceptable_alternatives: list[InvestigationDecision]
    hidden_regime_changes: list[int]
    hidden_anomalies: list[int]
    decision_severity: str  # low, medium, high, critical
    seed: int
    version: str = "benchmark-scenario-v1"
    watermark: str = "SYNTHETIC_BENCHMARK_FAMILY"
    sha256: str = "scenario-sha256"

    @property
    def anomaly_index(self) -> int:
        if self.hidden_anomalies:
            return self.hidden_anomalies[0]
        if self.hidden_regime_changes:
            return self.hidden_regime_changes[0]
        return 600


class ScenarioGenerator:
    """Generates 10 Controlled Investigation Benchmark Scenario Families (A through J)."""

    @classmethod
    def generate_scenario(cls, family: str, seed: int = 42, length: int = 1200) -> BenchmarkScenario:
        rng = np.random.default_rng(seed)
        t_axis = np.arange(length)

        if family == "A":
            # Family A: Transient Noise
            returns = rng.normal(0.0001, 0.008, length)
            returns[600] = 0.040  # single isolated benign spike
            expected = InvestigationDecision.CLOSE
            alts = [InvestigationDecision.WATCH]
            rc = []
            anom = [600]
            name = "Family A: Transient Noise"
            desc = "Isolated sampling spike with stationary background variance."
            sev = "low"

        elif family == "B":
            # Family B: Gradual Drift
            returns = rng.normal(0.0001, 0.007, length)
            # gradual variance inflation from t=600 to 1200
            scale = np.linspace(1.0, 3.5, length - 600)
            returns[600:] *= scale
            expected = InvestigationDecision.ESCALATE
            alts = [InvestigationDecision.WATCH]
            rc = [600]
            anom = [600]
            name = "Family B: Gradual Drift"
            desc = "Slowly escalating variance clustering over 600 time steps."
            sev = "high"

        elif family == "C":
            # Family C: Abrupt Structural Break
            returns = np.zeros(length)
            returns[:600] = rng.normal(0.0002, 0.006, 600)
            returns[600:] = rng.normal(-0.0015, 0.024, length - 600)
            expected = InvestigationDecision.ESCALATE
            alts = []
            rc = [600]
            anom = [600]
            name = "Family C: Abrupt Change Point"
            desc = "Discrete 4x volatility jump and negative drift at t=600."
            sev = "critical"

        elif family == "D":
            # Family D: Weak Coordinated Signal
            returns = rng.normal(0.0, 0.008, length)
            template = np.array([-0.015, -0.055, -0.10, -0.07, -0.02, 0.035, 0.072, 0.048, 0.018]) * 0.15
            for ev_t in [300, 600, 900]:
                returns[ev_t:ev_t + len(template)] += template
            expected = InvestigationDecision.ESCALATE
            alts = [InvestigationDecision.WATCH]
            rc = [300, 600, 900]
            anom = [300, 600, 900]
            name = "Family D: Weak Coordinated Signal"
            desc = "Sub-threshold multi-event repeated waveform alignment."
            sev = "high"

        elif family == "H":
            # Family H: Open-Set / Unknown Regime (Chaotic Cauchy / Levy Jump-Diffusion)
            returns = rng.standard_cauchy(length) * 0.005
            # Non-Gaussian heavy tailed burst
            expected = InvestigationDecision.DEFER
            alts = [InvestigationDecision.REQUEST_HUMAN_REVIEW, InvestigationDecision.ESCALATE]
            rc = [500]
            anom = [500]
            name = "Family H: Open-Set / Unknown Regime"
            desc = "Non-parametric heavy-tailed process incompatible with Gaussian models."
            sev = "critical"

        elif family == "I":
            # Family I: Adversarial Contamination
            returns = rng.normal(0.0001, 0.007, length)
            # inject misleading alternating impulses
            for idx in range(550, 650, 10):
                returns[idx] = 0.025 * (1 if idx % 20 == 0 else -1)
            expected = InvestigationDecision.ESCALATE
            alts = [InvestigationDecision.WATCH]
            rc = [550]
            anom = [550]
            name = "Family I: Adversarial Contamination"
            desc = "Artificially crafted adversarial impulse burst."
            sev = "high"

        else:
            # Default: Stationary with small regime transition
            returns = rng.normal(0.0001, 0.008, length)
            returns[700:] *= 1.8
            expected = InvestigationDecision.ESCALATE
            alts = [InvestigationDecision.WATCH]
            rc = [700]
            anom = [700]
            name = f"Family {family}: Ambiguous Regime"
            desc = "Ambiguous variance shift scenario."
            sev = "medium"

        price = 100.0 * np.exp(np.cumsum(returns))
        volume = rng.lognormal(mean=11.0, sigma=0.2, size=length)

        return BenchmarkScenario(
            scenario_id=f"scen-{family.lower()}-{seed}",
            family=family,
            name=name,
            description=desc,
            returns=returns,
            price=price,
            volume=volume,
            time=t_axis,
            expected_decision=expected,
            acceptable_alternatives=alts,
            hidden_regime_changes=rc,
            hidden_anomalies=anom,
            decision_severity=sev,
            seed=seed,
            sha256=f"sha256-fam-{family}-{seed}",
        )
