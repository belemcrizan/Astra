from __future__ import annotations

import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any

from ..adapters.synthetic import SyntheticMarketAdapter
from ..config import Settings
from ..contracts import InvestigationDecision, InvestigationReport
from ..datasets import generate_synthetic_market
from ..evaluation import evaluate_detections, wilson_interval
from ..investigation.engine import InvestigationEngine
from ..preregistration import PREREGISTRATION, preregistration_hash
from ..stacking import event_stacking_test


class BenchmarkRunner:
    """Runs scientific benchmarks, comparative investigation baselines, and ablations for ASTRA v0.3."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()

    async def run_investigation_benchmark(self, seed_count: int = 30, points: int = 2400) -> dict[str, Any]:
        engine = InvestigationEngine(self.settings)
        rows: list[dict[str, Any]] = []

        for seed in range(seed_count):
            market = generate_synthetic_market(points=points, seed=seed)
            report = await engine.investigate(market, strategy="evidence_driven", force_reprocess=True)
            eval_data = report.scientific_evaluation

            # H2 zero-signal null test
            null_data = generate_synthetic_market(points=points, seed=seed, signal_amplitude=0.0)
            stacking_cfg = PREREGISTRATION["stacking"]
            null_stacking = event_stacking_test(
                null_data.returns,
                null_data.event_indicator,
                null_data.template,
                permutations=stacking_cfg["permutations"],
                alpha=stacking_cfg["alpha"],
                seed=seed,
            )

            rows.append({
                "seed": seed,
                "latency_ms": report.metrics["total_latency_ms"],
                "cost_units": report.metrics["cost_units_used"],
                "tests_used": report.metrics["tests_executed_count"],
                "decision": report.metrics["decision"],
                "regime": eval_data["regime_metrics"],
                "anomaly": eval_data["anomaly_metrics"],
                "baselines": {name: item["metrics"] for name, item in eval_data["baselines"].items()},
                "h2_p_value": eval_data["stacking_h2"].get("p_value"),
                "h2_null_p_value": null_stacking.p_value,
                "hypotheses_falsified": sum(h.status == "falsified" for h in report.competing_hypotheses),
            })

        total_points = seed_count * points
        latencies = sorted(float(r["latency_ms"]) for r in rows)
        costs = sorted(float(r["cost_units"]) for r in rows)
        h2_hits = sum(int(r["h2_p_value"] <= PREREGISTRATION["stacking"]["alpha"]) for r in rows if r["h2_p_value"] is not None)
        h2_null_hits = sum(int(r["h2_null_p_value"] <= PREREGISTRATION["stacking"]["alpha"]) for r in rows)

        baseline_names = sorted(rows[0]["baselines"].keys())

        summary = {
            "scope": "synthetic_controlled_benchmark_not_external_validation",
            "methodology_version": PREREGISTRATION["methodology_version"],
            "preregistration_sha256": preregistration_hash(),
            "runs": seed_count,
            "points_per_run": points,
            "astra_regime": _aggregate([r["regime"] for r in rows], total_points),
            "astra_anomaly": _aggregate([r["anomaly"] for r in rows], total_points),
            "baselines": {name: _aggregate([r["baselines"][name] for r in rows], total_points) for name in baseline_names},
            "h2_significant_rate_at_preregistered_alpha": h2_hits / seed_count,
            "h2_significant_rate_ci95": wilson_interval(h2_hits, seed_count),
            "h2_false_positive_rate_under_zero_signal": h2_null_hits / seed_count,
            "h2_false_positive_rate_ci95": wilson_interval(h2_null_hits, seed_count),
            "latency_p50_ms": statistics.median(latencies),
            "latency_p95_ms": latencies[min(len(latencies) - 1, round(0.95 * (len(latencies) - 1)))],
            "cost_p50_units": statistics.median(costs),
            "mean_tests_per_investigation": statistics.mean(r["tests_used"] for r in rows),
            "mean_falsified_hypotheses": statistics.mean(r["hypotheses_falsified"] for r in rows),
        }

        output_path = self.settings.output_dir / "reports" / "benchmark-v0.3-latest.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({"summary": summary, "runs": rows}, indent=2), encoding="utf-8")
        output_path.with_suffix(".md").write_text(_render_benchmark_markdown(summary), encoding="utf-8")

        return {"summary": summary, "output_file": str(output_path)}

    async def run_ablations_benchmark(self, seeds: int = 15, points: int = 2400) -> dict[str, Any]:
        """Runs the 5 ablation configurations to isolate value of each component."""
        engine = InvestigationEngine(self.settings)
        configs = [
            ("ASTRA Full (Evidence-Driven)", "evidence_driven"),
            ("ASTRA Fixed-Sequence (No Evidence Selection)", "fixed"),
            ("ASTRA Falsification-Only (No Score Balance)", "falsification_only"),
        ]

        ablation_results: dict[str, Any] = {}

        for name, strat in configs:
            run_records = []
            for seed in range(seeds):
                market = generate_synthetic_market(points=points, seed=seed)
                rep = await engine.investigate(market, strategy=strat, force_reprocess=True)
                run_records.append({
                    "decision": rep.decision_outcome.decision.value if rep.decision_outcome else "UNKNOWN",
                    "escalated": bool(rep.decision_outcome and rep.decision_outcome.decision == InvestigationDecision.ESCALATE),
                    "tests": rep.budget.tests_used,
                    "cost": rep.budget.cost_units_used,
                    "latency_ms": rep.metrics["total_latency_ms"],
                    "falsified_count": sum(h.status == "falsified" for h in rep.competing_hypotheses),
                })
            
            escalations = sum(int(r["escalated"]) for r in run_records)
            ablation_results[name] = {
                "strategy": strat,
                "runs": seeds,
                "escalation_rate": escalations / seeds,
                "escalation_rate_ci95": wilson_interval(escalations, seeds),
                "mean_tests": round(statistics.mean(r["tests"] for r in run_records), 2),
                "mean_cost_units": round(statistics.mean(r["cost"] for r in run_records), 2),
                "mean_falsified_count": round(statistics.mean(r["falsified_count"] for r in run_records), 2),
                "latency_p50_ms": round(statistics.median(r["latency_ms"] for r in run_records), 2),
            }

        output_path = self.settings.output_dir / "reports" / "ablations-v0.3-latest.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(ablation_results, indent=2), encoding="utf-8")
        output_path.with_suffix(".md").write_text(_render_ablations_markdown(ablation_results), encoding="utf-8")

        return ablation_results


def _aggregate(items: list[dict], total_points: int) -> dict:
    tp = sum(int(item["true_positives"]) for item in items)
    fp = sum(int(item["false_positives"]) for item in items)
    fn = sum(int(item["false_negatives"]) for item in items)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    delays = [prediction - actual for item in items for actual, prediction in item.get("matched_pairs", [])]
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "precision_ci95": wilson_interval(tp, tp + fp),
        "recall": recall,
        "recall_ci95": wilson_interval(tp, tp + fn),
        "f1": f1,
        "false_alarms_per_1000": 1000 * fp / max(total_points, 1),
        "mean_signed_delay": statistics.mean(delays) if delays else None,
        "mean_absolute_delay": statistics.mean(abs(delay) for delay in delays) if delays else None,
    }


def _render_benchmark_markdown(summary: dict) -> str:
    lines = [
        "# ASTRA v0.3 — Scientific Benchmark Summary",
        "",
        "> Controlled synthetic evaluation for statistical sanity testing. Does not constitute external real-world validation.",
        "",
        "| Detector / Method | Precision | Recall | F1 | False Alarms / 1k | Mean Abs. Delay |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    methods = {"ASTRA (Detection Kernel)": summary["astra_regime"], **summary["baselines"]}
    for name, item in methods.items():
        delay_str = "n/a" if item["mean_absolute_delay"] is None else f"{item['mean_absolute_delay']:.2f}"
        lines.append(
            f"| {name} | {item['precision']:.1%} | {item['recall']:.1%} | {item['f1']:.1%} | {item['false_alarms_per_1000']:.3f} | {delay_str} |"
        )

    lines += [
        "",
        f"- **Runs Evaluated:** {summary['runs']} seeds ({summary['points_per_run']} points each)",
        f"- **Latency p95:** {summary['latency_p95_ms']:.2f} ms",
        f"- **Mean Tests / Investigation:** {summary['mean_tests_per_investigation']:.1f}",
        f"- **Mean Hypotheses Falsified / Run:** {summary['mean_falsified_hypotheses']:.1f}",
        f"- **Methodology SHA-256:** `{summary['preregistration_sha256']}`",
        f"- **H2 Signal Power (Fixed Signal):** {summary['h2_significant_rate_at_preregistered_alpha']:.1%} (95% CI {summary['h2_significant_rate_ci95']})",
        f"- **H2 False Positive Rate (Zero Signal):** {summary['h2_false_positive_rate_under_zero_signal']:.1%} (95% CI {summary['h2_false_positive_rate_ci95']})",
        "",
    ]
    return "\n".join(lines)


def _render_ablations_markdown(ablations: dict) -> str:
    lines = [
        "# ASTRA v0.3 — Investigation Ablation Results",
        "",
        "| Configuration | Escalation Rate | Mean Tests | Mean Cost Units | Mean Falsified | Latency p50 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, res in ablations.items():
        lines.append(
            f"| {name} | {res['escalation_rate']:.1%} | {res['mean_tests']:.1f} | {res['mean_cost_units']:.1f} | {res['mean_falsified_count']:.1f} | {res['latency_p50_ms']:.1f} ms |"
        )
    lines.append("")
    return "\n".join(lines)


async def run_full_benchmark(seeds: int = 30, points: int = 2400) -> dict[str, Any]:
    return await BenchmarkRunner().run_investigation_benchmark(seed_count=seeds, points=points)


async def run_ablations_benchmark(seeds: int = 15, points: int = 2400) -> dict[str, Any]:
    return await BenchmarkRunner().run_ablations_benchmark(seeds=seeds, points=points)
