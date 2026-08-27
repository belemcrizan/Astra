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


class VoIEngine:
    """Computes Expected Information Gain (EIG), Expected Falsification Gain (EFG),
    Expected Decision-Relevance (EDR), and Value of Information (VoI).
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
            # Measures discrimination overlap between top competing hypotheses
            overlap = len(top_pair.intersection(set(spec.discriminates)))
            score_diff = abs(h_lead.evidence_score - h_second.evidence_score)
            closeness_factor = float(1.0 / (1.0 + 2.0 * score_diff))
            eig = (overlap / max(len(spec.discriminates), 1)) * closeness_factor

            # 2. Expected Falsification Gain (EFG)
            # Measures probability/utility of disproving the leading plausible hypothesis
            is_lead_targeted = h_lead.id in spec.discriminates
            lead_falsification_importance = 1.0 if h_lead.id in ("H1", "H2", "H3", "H4") else 0.5
            efg = (0.85 if is_lead_targeted else 0.20) * lead_falsification_importance * (1.0 - (0.3 * h_lead.falsification_attempts))
            efg = float(np.clip(efg, 0.0, 1.0))

            # 3. Expected Decision Relevance (EDR)
            # Higher if top hypotheses imply different decision outcomes (e.g. H1->CLOSE vs H2/H3->ESCALATE)
            h_lead_implies_escalate = h_lead.id in ("H2", "H3", "H4")
            h_second_implies_escalate = h_second.id in ("H2", "H3", "H4")
            decision_divergence = 1.0 if (h_lead_implies_escalate != h_second_implies_escalate) else 0.4
            edr = float(eig * decision_divergence)

            # 4. Costs, Latencies, Risk Penalties
            cost = spec.cost_units
            latency = 5.0 * cost  # approximate expected ms
            risk_penalty = 0.05 * cost

            # Budget penalty multiplier if budget is running low
            budget_remaining_ratio = max(0.01, (budget.max_cost_units - budget.cost_units_used) / budget.max_cost_units)
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
            # VoI(a) = Net decision improvement - Cost
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

        # Sort descending by net utility
        estimates.sort(key=lambda x: x.net_utility, reverse=True)
        if estimates:
            estimates[0].selected = True

        return estimates
