"""ASTRA Canonical Scenario Registry.

Single source of truth for benchmark scenarios across CLI, API, UI, benchmarks, and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import numpy as np

from ..contracts import InvestigationDecision


@dataclass
class ScenarioDefinition:
    """Metadata and specification for an investigation scenario."""
    id: str
    family: str
    display_name: str
    description: str
    default_seed: int
    trigger_index: int
    expected_decision: InvestigationDecision
    acceptable_alternatives: list[InvestigationDecision]
    semantic_expectation: str
    demo_purpose: str


class ScenarioRegistry:
    """Canonical registry and factory for all ASTRA investigation scenarios."""

    _DEFINITIONS: dict[str, ScenarioDefinition] = {
        "hero": ScenarioDefinition(
            id="hero",
            family="C",
            display_name="Hero: Abrupt Regime Break (Family C)",
            description="Discrete 4x volatility jump and negative drift at t=600.",
            default_seed=42,
            trigger_index=600,
            expected_decision=InvestigationDecision.ESCALATE,
            acceptable_alternatives=[],
            semantic_expectation="Initial transient noise hypothesis is falsified by window contrast & changepoint tests, promoting structural regime change.",
            demo_purpose="Demonstrates hypothesis trap recovery, targeted falsification, and rational belief revision.",
        ),
        "control": ScenarioDefinition(
            id="control",
            family="A",
            display_name="Control: Benign Noise Safe Closure (Family A)",
            description="Isolated sampling spike with stationary background variance.",
            default_seed=42,
            trigger_index=600,
            expected_decision=InvestigationDecision.CLOSE,
            acceptable_alternatives=[InvestigationDecision.WATCH],
            semantic_expectation="Transient fluctuation (H1) survives discriminative tests; structural break hypotheses are refuted, halting investigation with non-positive VoI.",
            demo_purpose="Demonstrates false alarm prevention and rational early stopping on benign noise.",
        ),
        "unknown": ScenarioDefinition(
            id="unknown",
            family="H",
            display_name="Unknown: Heavy-Tailed Open Set (Family H)",
            description="Non-parametric heavy-tailed Cauchy process incompatible with Gaussian models.",
            default_seed=42,
            trigger_index=500,
            expected_decision=InvestigationDecision.DEFER,
            acceptable_alternatives=[InvestigationDecision.REQUEST_HUMAN_REVIEW, InvestigationDecision.ESCALATE],
            semantic_expectation="Known parametric models collectively fail; excess kurtosis elevates H_unknown, triggering refusal of forced classification.",
            demo_purpose="Demonstrates functional open-set recognition and safe deferral to human review.",
        ),
        "budget": ScenarioDefinition(
            id="budget",
            family="B",
            display_name="Budget: Gradual Drift Sensitivity (Family B)",
            description="Slowly escalating variance clustering over 600 time steps.",
            default_seed=42,
            trigger_index=600,
            expected_decision=InvestigationDecision.ESCALATE,
            acceptable_alternatives=[InvestigationDecision.WATCH],
            semantic_expectation="Investigation depth and test selection adapt dynamically to allocated resource budget.",
            demo_purpose="Demonstrates multi-attribute Value of Information cost-awareness and anytime stopping.",
        ),
        "adversarial": ScenarioDefinition(
            id="adversarial",
            family="I",
            display_name="Adversarial: Impulse Burst Stress (Family I)",
            description="Artificially crafted adversarial impulse burst.",
            default_seed=42,
            trigger_index=550,
            expected_decision=InvestigationDecision.ESCALATE,
            acceptable_alternatives=[InvestigationDecision.WATCH],
            semantic_expectation="Robust z-scores and sandboxed DSL resist parameter manipulation and boundary violation attempts.",
            demo_purpose="Demonstrates fault injection resilience and security boundary enforcement.",
        ),
        "multimodal": ScenarioDefinition(
            id="multimodal",
            family="D",
            display_name="Multimodal: Coordinated Weak Signal (Family D)",
            description="Sub-threshold multi-event repeated waveform alignment with analyst document.",
            default_seed=42,
            trigger_index=600,
            expected_decision=InvestigationDecision.ESCALATE,
            acceptable_alternatives=[InvestigationDecision.WATCH],
            semantic_expectation="External untrusted analyst claims are cross-checked and verified against empirical series.",
            demo_purpose="Demonstrates sandboxed multimodal claim verification without trusting unstructured text blindly.",
        ),
        "real_world": ScenarioDefinition(
            id="real_world",
            family="REAL",
            display_name="Real Market: Empirical Volatility Shock (Track B)",
            description="Real market historical volatility shock (SPY 2020 regime break).",
            default_seed=42,
            trigger_index=600,
            expected_decision=InvestigationDecision.ESCALATE,
            acceptable_alternatives=[InvestigationDecision.WATCH],
            semantic_expectation="Evaluates empirical series under Track B without claiming synthetic ground truth.",
            demo_purpose="Demonstrates real-world applicability on genuine market time series.",
        ),
    }

    @classmethod
    def get(cls, scenario_id: str) -> ScenarioDefinition | None:
        """Retrieves scenario metadata by ID or family letter."""
        sid = scenario_id.lower().strip()
        if sid in cls._DEFINITIONS:
            return cls._DEFINITIONS[sid]
        for defn in cls._DEFINITIONS.values():
            if defn.family.lower() == sid:
                return defn
        return None

    @classmethod
    def list_scenarios(cls) -> list[ScenarioDefinition]:
        """Returns all registered scenarios in canonical order."""
        return list(cls._DEFINITIONS.values())

    @classmethod
    def generate(cls, scenario_id: str, seed: int | None = None, length: int = 1200) -> Any:
        """Generates the concrete BenchmarkScenario for the given identifier."""
        from ..benchmarks.scenarios import ScenarioGenerator
        defn = cls.get(scenario_id)
        fam = defn.family if defn else (scenario_id.upper() if len(scenario_id) == 1 else "C")
        s = seed if seed is not None else (defn.default_seed if defn else 42)
        return ScenarioGenerator.generate_scenario(fam, seed=s, length=length)
