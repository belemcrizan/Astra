from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any
import numpy as np

from ..config import Settings
from ..contracts import InvestigationBudget, InvestigationDecision
from ..investigation.engine import InvestigationEngine
from .oracle import PrivilegedOracle
from .pareto import ParetoFrontierAnalyzer
from .scenarios import ScenarioGenerator


class InvestigationBenchmarkRunner:
    """Runs Multi-Seed Investigation Benchmarks, Policy Baselines, and Ablations for ASTRA v0.4."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()

    async def run_investigation_benchmark(self, seeds: int = 30) -> dict[str, Any]:
        """Runs the investigation benchmark across multiple families and seeds."""
        engine = InvestigationEngine(self.settings)
        families = ["A", "B", "C", "D", "H", "I"]
        results: list[dict[str, Any]] = []

        for seed in range(seeds):
            fam = families[seed % len(families)]
            scenario = ScenarioGenerator.generate_scenario(fam, seed=seed)
            
            t0 = time.perf_counter()
            report = await engine.investigate(scenario, strategy="evidence_driven", force_reprocess=True)
            latency = (time.perf_counter() - t0) * 1000

            dec = report.decision_outcome.decision if report.decision_outcome else InvestigationDecision.REQUEST_HUMAN_REVIEW
            regret_info = PrivilegedOracle.calculate_regret(
                scenario=scenario,
                policy_decision=dec,
                policy_cost=report.budget.cost_units_used,
                policy_tests=report.budget.tests_used,
            )

            results.append({
                "seed": seed,
                "family": fam,
                "decision": dec.value,
                "expected_decision": scenario.expected_decision.value,
                "is_correct": regret_info["is_correct_resolution"],
                "cost_units": report.budget.cost_units_used,
                "tests_used": report.budget.tests_used,
                "stop_reason": report.stop_reason.value,
                "latency_ms": latency,
                "cost_regret": regret_info["cost_regret"],
                "unknown_score": report.unknown_score,
            })

        acc = float(np.mean([r["is_correct"] for r in results]))
        mean_cost = float(np.mean([r["cost_units"] for r in results]))
        mean_tests = float(np.mean([r["tests_used"] for r in results]))
        p95_lat = float(np.percentile([r["latency_ms"] for r in results], 95))
        mean_regret = float(np.mean([r["cost_regret"] for r in results]))

        summary = {
            "runs": len(results),
            "investigation_accuracy": round(acc * 100.0, 1),
            "mean_cost_units": round(mean_cost, 2),
            "mean_tests_used": round(mean_tests, 2),
            "latency_p95_ms": round(p95_lat, 1),
            "mean_oracle_cost_regret": round(mean_regret, 2),
            "detailed_runs": results,
        }

        # Save artifact
        out_dir = self.settings.output_dir / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "investigation-benchmark-v0.4-latest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        return summary

    async def run_investigation_ablations(self, seeds: int = 15) -> dict[str, Any]:
        """Runs ablation suite comparing Full Adaptive ASTRA against baselines."""
        engine = InvestigationEngine(self.settings)
        policies = ["evidence_driven", "fixed_sequence", "falsification_only"]
        families = ["A", "B", "C", "D", "H"]
        policy_runs: dict[str, list[dict[str, Any]]] = {p: [] for p in policies}

        for p in policies:
            for seed in range(seeds):
                fam = families[seed % len(families)]
                scenario = ScenarioGenerator.generate_scenario(fam, seed=seed)
                
                t0 = time.perf_counter()
                report = await engine.investigate(scenario, strategy=p, force_reprocess=True)
                latency = (time.perf_counter() - t0) * 1000

                dec = report.decision_outcome.decision if report.decision_outcome else InvestigationDecision.REQUEST_HUMAN_REVIEW
                regret_info = PrivilegedOracle.calculate_regret(
                    scenario=scenario,
                    policy_decision=dec,
                    policy_cost=report.budget.cost_units_used,
                    policy_tests=report.budget.tests_used,
                )

                policy_runs[p].append({
                    "is_correct": regret_info["is_correct_resolution"],
                    "cost_units": report.budget.cost_units_used,
                    "tests_used": report.budget.tests_used,
                    "latency_ms": latency,
                    "cost_regret": regret_info["cost_regret"],
                })

        pareto_table = ParetoFrontierAnalyzer.evaluate_pareto_frontier(policy_runs)
        return {
            "runs_per_policy": seeds,
            "pareto_frontier": pareto_table,
        }

    async def run_pareto_frontier(self, seeds: int = 15) -> list[dict[str, Any]]:
        """Convenience method returning the Pareto frontier table."""
        res = await self.run_investigation_ablations(seeds=seeds)
        pareto_table = res["pareto_frontier"]
        self.export_latest_artifacts(pareto_table, seeds=seeds)
        return pareto_table

    def export_latest_artifacts(self, pareto_table: list[dict[str, Any]], seeds: int = 15) -> None:
        """Exports reproducible benchmark artifacts to artifacts/benchmarks/latest.json and latest.csv."""
        bench_dir = Path("artifacts") / "benchmarks"
        bench_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_data = {
            "version": "0.4.2",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seeds_per_policy": seeds,
            "families": ["A", "B", "C", "D", "H"],
            "methodology_sha256": "1b2eeaeb0a3f842cb4afaab755bd27fee469b818e05298bdbfd64d73ac0975a4",
            "pareto_frontier": pareto_table,
        }
        
        # Save JSON
        (bench_dir / "latest.json").write_text(json.dumps(artifact_data, indent=2), encoding="utf-8")
        
        # Save CSV
        csv_lines = ["policy,accuracy_pct,mean_cost_units,p95_latency_ms,pareto_efficient"]
        for p in pareto_table:
            csv_lines.append(f"{p['policy']},{p['accuracy']},{p['mean_cost']},{p['p95_latency_ms']},{p['pareto_efficient']}")
        (bench_dir / "latest.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

