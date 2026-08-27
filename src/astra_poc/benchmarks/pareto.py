from __future__ import annotations

from typing import Any
import numpy as np


class ParetoFrontierAnalyzer:
    """Computes Quality-Cost and Latency-Quality Pareto Frontiers for investigation policies."""

    @classmethod
    def evaluate_pareto_frontier(
        cls,
        policy_results: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Evaluates mean metrics and identifies Pareto-efficient policies."""
        summaries: list[dict[str, Any]] = []

        for policy_name, runs in policy_results.items():
            if not runs:
                continue
            accuracy = float(np.mean([r.get("is_correct", 0.0) for r in runs]))
            cost = float(np.mean([r.get("cost_units", 0.0) for r in runs]))
            latencies = [r.get("latency_ms", 10.0) for r in runs]
            p50_lat = float(np.median(latencies))
            p95_lat = float(np.percentile(latencies, 95))
            cost_regret = float(np.mean([r.get("cost_regret", 0.0) for r in runs]))

            summaries.append({
                "policy": policy_name,
                "accuracy": round(accuracy * 100.0, 1),
                "mean_cost": round(cost, 2),
                "p50_latency_ms": round(p50_lat, 1),
                "p95_latency_ms": round(p95_lat, 1),
                "cost_regret": round(cost_regret, 2),
                "pareto_efficient": False,
            })

        # Identify Pareto-optimal policies: A policy is Pareto-efficient if no other policy has BOTH lower cost AND higher accuracy
        for s1 in summaries:
            dominated = False
            for s2 in summaries:
                if s2["policy"] == s1["policy"]:
                    continue
                if s2["mean_cost"] <= s1["mean_cost"] and s2["accuracy"] >= s1["accuracy"] and (s2["mean_cost"] < s1["mean_cost"] or s2["accuracy"] > s1["accuracy"]):
                    dominated = True
                    break
            s1["pareto_efficient"] = not dominated

        return sorted(summaries, key=lambda x: x["mean_cost"])
