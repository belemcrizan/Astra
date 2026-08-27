from __future__ import annotations

from typing import Any
import numpy as np

from ..contracts import (
    ActionUtilityEstimate,
    DSLOperation,
    DSLOperationName,
    InvestigationBudget,
    InvestigationHypothesis,
)
from ..execution.dsl import DSL_OPERATION_SPECS, DSLOperationSpec


# Direct test power table mapping hypothesis to operations with high falsification power
HYPOTHESIS_FALSIFICATION_POWER: dict[str, dict[DSLOperationName, float]] = {
    "H1": {
        DSLOperationName.COMPARE_WINDOWS: 0.95,
        DSLOperationName.RUN_PELT: 0.92,
        DSLOperationName.RUN_CUSUM: 0.85,
        DSLOperationName.RUN_PAGE_HINKLEY: 0.80,
        DSLOperationName.CALCULATE_ENTROPY: 0.60,
        DSLOperationName.CHECK_SUSCEPTIBILITY: 0.55,
    },
    "H2": {
        DSLOperationName.RUN_PAGE_HINKLEY: 0.92,
        DSLOperationName.RUN_CUSUM: 0.88,
        DSLOperationName.RUN_PELT: 0.82,
        DSLOperationName.CALCULATE_ENTROPY: 0.80,
        DSLOperationName.COMPARE_WINDOWS: 0.75,
        DSLOperationName.CHECK_SUSCEPTIBILITY: 0.70,
    },
    "H3": {
        DSLOperationName.RUN_PELT: 0.95,
        DSLOperationName.RUN_BOCPD: 0.90,
        DSLOperationName.COMPARE_WINDOWS: 0.85,
        DSLOperationName.RUN_PAGE_HINKLEY: 0.75,
        DSLOperationName.RUN_CUSUM: 0.70,
    },
    "H4": {
        DSLOperationName.TEST_TEMPORAL_STACKING: 0.95,
        DSLOperationName.COMPARE_WINDOWS: 0.60,
        DSLOperationName.RUN_CUSUM: 0.50,
    },
    "H_unknown": {
        DSLOperationName.REQUEST_FEATURE: 0.85,
        DSLOperationName.CALCULATE_ENTROPY: 0.80,
        DSLOperationName.CHECK_SUSCEPTIBILITY: 0.75,
    },
}


class VoIEngine:
    """Computes Expected Information Gain (EIG), Expected Falsification Gain (EFG),
    Expected Decision-Relevance (EDR), and Value of Information (VoI) for ASTRA v0.4.1.
    """

    @classmethod
    def evaluate_candidates(
        cls,
        ranked_hypotheses: list[InvestigationHypothesis],
        budget: InvestigationBudget,
        executed_ops: set[DSLOperationName],
        unknown_score: float = 0.20,
        alpha_weight: float = 1.2,
        beta_weight: float = 1.5,
        gamma_weight: float = 1.0,
        cost_lambda: float = 0.35,
        risk_lambda: float = 0.20,
    ) -> list[ActionUtilityEstimate]:
        if len(ranked_hypotheses) < 2:
            return []

        h_lead = ranked_hypotheses[0]
        h_second = ranked_hypotheses[1]
        top_pair = {h_lead.id, h_second.id}

        estimates: list[ActionUtilityEstimate] = []

        for op_name, spec in DSL_OPERATION_SPECS.items():
            if op_name in executed_ops:
                continue

            # Meta operations are evaluated in stopping policy
            if op_name in (DSLOperationName.RECOMMEND_DECISION, DSLOperationName.EVALUATE_HYPOTHESIS, DSLOperationName.ASK_HUMAN):
                continue

            # 1. Expected Information Gain (EIG)
            # Measures discrimination capability between the top competing pair
            overlap = len(top_pair.intersection(set(spec.discriminates)))
            score_diff = abs(h_lead.evidence_score - h_second.evidence_score)
            closeness_factor = float(1.0 / (1.0 + 2.0 * score_diff))
            eig = float(min(1.0, overlap / 2.0) * closeness_factor)

            # 2. Expected Falsification Gain (EFG)
            # Measures targeted power to falsify the current leading hypothesis
            power_dict = HYPOTHESIS_FALSIFICATION_POWER.get(h_lead.id, {})
            base_power = power_dict.get(op_name, 0.40 if h_lead.id in spec.discriminates else 0.15)
            # Diminishing returns if leading hypothesis has already been challenged
            attempt_penalty = max(0.2, 1.0 - (0.25 * h_lead.falsification_attempts))
            efg = float(np.clip(base_power * attempt_penalty, 0.0, 1.0))

            # 3. Expected Decision Relevance (EDR)
            # Higher if top hypotheses imply divergent decisions (e.g. H1->CLOSE vs H2/H3->ESCALATE vs H_unknown->DEFER)
            action_map = {"H1": "CLOSE", "H_unknown": "DEFER", "H2": "ESCALATE", "H3": "ESCALATE", "H4": "ESCALATE"}
            h_lead_act = action_map.get(h_lead.id, "WATCH")
            h_second_act = action_map.get(h_second.id, "WATCH")
            decision_divergence = 1.0 if (h_lead_act != h_second_act) else 0.35
            edr = float(eig * decision_divergence)

            # 4. Costs, Latencies, Risk Penalties
            cost = spec.cost_units
            latency = 4.0 * cost  # ms
            risk_penalty = 0.05 * cost

            # Budget sensitivity scaling
            budget_remaining_ratio = max(0.05, (budget.max_cost_units - budget.cost_units_used) / max(budget.max_cost_units, 1.0))
            effective_cost_lambda = cost_lambda / budget_remaining_ratio

            # 5. Net Utility: U(a) = α·EIG + β·EFG + γ·EDR - λ_c·C - λ_r·R
            net_utility = (
                alpha_weight * eig
                + beta_weight * efg
                + gamma_weight * edr
                - effective_cost_lambda * cost
                - risk_lambda * risk_penalty
            )

            # 6. Value of Information (VoI)
            voi = (alpha_weight * eig + beta_weight * efg + gamma_weight * edr) - (cost * 0.40)

            reason = (
                f"EIG={eig:.2f}, EFG={efg:.2f}, EDR={edr:.2f} | "
                f"Cost={cost:.1f}u | Net Utility={net_utility:.2f} | VoI={voi:.2f}"
            )

            estimates.append(ActionUtilityEstimate(
                action=op_name,
                expected_info_gain=round(eig, 3),
                expected_falsification_gain=round(efg, 3),
                expected_decision_gain=round(edr, 3),
                cost=cost,
                latency_ms=round(latency, 1),
                risk_penalty=round(risk_penalty, 3),
                net_utility=round(net_utility, 3),
                voi=round(voi, 3),
                selected=False,
                reasoning=reason,
            ))

        # Deterministic tie-breaking sort:
        # 1. Higher Net Utility
        # 2. Higher Expected Falsification Gain
        # 3. Higher Expected Info Gain
        # 4. Lower Cost
        # 5. Lower Latency
        # 6. Stable Lexical ordering
        estimates.sort(
            key=lambda x: (
                -round(x.net_utility, 4),
                -round(x.expected_falsification_gain, 4),
                -round(x.expected_info_gain, 4),
                round(x.cost, 4),
                round(x.latency_ms, 4),
                x.action.value,
            )
        )
        if estimates:
            estimates[0].selected = True

        return estimates
