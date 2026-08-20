from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import shutil
from pathlib import Path

from .config import Settings
from .contracts import InvestigationReport
from .datasets import generate_synthetic_market
from .evaluation import wilson_interval
from .orchestrator import OrchestratorAgent
from .preregistration import PREREGISTRATION, preregistration_hash
from .stacking import event_stacking_test


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astra", description="ASTRA v0.2 - POC cientifica local e segura")
    sub = parser.add_subparsers(dest="command")
    demo = sub.add_parser("demo", help="executa uma investigacao sintetica completa")
    demo.add_argument("--seed", type=int, default=None, help="semente reproduzivel (padrao: 42)")
    demo.add_argument("--points", type=int, default=None, help="quantidade de observacoes (minimo: 600)")
    benchmark = sub.add_parser("benchmark", help="repete a POC e agrega metricas com IC95%")
    benchmark.add_argument("--seeds", type=int, default=30, help="quantidade de sementes (padrao: 30)")
    benchmark.add_argument("--points", type=int, default=2400, help="observacoes por execucao")
    sub.add_parser("schema", help="exporta o JSON Schema versionado do relatorio")
    sub.add_parser("preregistration", help="exibe metodologia e hash dos limiares pre-registrados")
    sub.add_parser("clean", help="remove apenas resultados gerados em artifacts")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "clean":
        shutil.rmtree("artifacts/runs", ignore_errors=True)
        shutil.rmtree("artifacts/reports", ignore_errors=True)
        print("Resultados locais removidos. Codigo, testes e documentacao foram preservados.")
        return
    if args.command == "schema":
        output = Path("artifacts/report-schema-v0.2.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(InvestigationReport.model_json_schema(), indent=2), encoding="utf-8")
        print(f"JSON Schema: {output}")
        return
    if args.command == "preregistration":
        print(json.dumps(PREREGISTRATION, indent=2, ensure_ascii=False))
        print(f"SHA-256: {preregistration_hash()}")
        return
    if args.command == "benchmark":
        asyncio.run(run_benchmark(args.seeds, args.points))
        return
    if args.command not in {None, "demo"}:
        raise SystemExit(2)
    settings = Settings.from_env()
    if getattr(args, "seed", None) is not None:
        settings.seed = args.seed
    if getattr(args, "points", None) is not None:
        settings.points = args.points
    report = asyncio.run(OrchestratorAgent(settings).investigate())
    regime = report.scientific_evaluation["regime_metrics"]
    anomaly = report.scientific_evaluation["anomaly_metrics"]
    h2 = report.scientific_evaluation["stacking_h2"]
    print("\nASTRA v0.2 concluiu o teste de sanidade sintetico")
    print(f"Run ID: {report.run_id}")
    print(f"Decisao: {report.governance.decision.value}")
    print(f"Regimes: precision={regime['precision']:.1%}, recall={regime['recall']:.1%}, F1={regime['f1']:.1%}")
    print(f"Atraso absoluto medio: {regime['mean_absolute_delay']} pontos")
    print(f"Anomalias: precision={anomaly['precision']:.1%}, recall={anomaly['recall']:.1%}, F1={anomaly['f1']:.1%}")
    print(f"H2 stacking: p={h2.get('p_value', float('nan')):.4f}, alpha={h2.get('alpha', float('nan')):.4f}")
    print(f"Latencia total: {report.metrics['total_latency_ms']} ms")
    print(f"Relatorio humano: artifacts/reports/{report.run_id}.md")
    print("Aviso: teste sintetico, evidence scores nao calibrados e revisao humana obrigatoria.")


def _aggregate(items: list[dict], total_points: int) -> dict:
    tp = sum(int(item["true_positives"]) for item in items)
    fp = sum(int(item["false_positives"]) for item in items)
    fn = sum(int(item["false_negatives"]) for item in items)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    delays = [prediction - actual for item in items for actual, prediction in item["matched_pairs"]]
    return {
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": precision, "precision_ci95": wilson_interval(tp, tp + fp),
        "recall": recall, "recall_ci95": wilson_interval(tp, tp + fn),
        "f1": f1, "false_alarms_per_1000": 1000 * fp / max(total_points, 1),
        "mean_signed_delay": statistics.mean(delays) if delays else None,
        "mean_absolute_delay": statistics.mean(abs(delay) for delay in delays) if delays else None,
    }


async def run_benchmark(seed_count: int, points: int) -> None:
    if not 1 <= seed_count <= 500:
        raise SystemExit("--seeds deve estar entre 1 e 500")
    rows: list[dict] = []
    for seed in range(seed_count):
        report = await OrchestratorAgent(Settings(seed=seed, points=points)).investigate()
        evaluation = report.scientific_evaluation
        null_data = generate_synthetic_market(points=points, seed=seed, signal_amplitude=0.0)
        stacking_config = PREREGISTRATION["stacking"]
        null_stacking = event_stacking_test(
            null_data.returns, null_data.event_indicator, null_data.template,
            permutations=stacking_config["permutations"], alpha=stacking_config["alpha"], seed=seed,
        )
        rows.append({
            "seed": seed,
            "latency_ms": report.metrics["total_latency_ms"],
            "regime": evaluation["regime_metrics"],
            "anomaly": evaluation["anomaly_metrics"],
            "baselines": {name: item["metrics"] for name, item in evaluation["baselines"].items()},
            "h2_p_value": evaluation["stacking_h2"].get("p_value"),
            "h2_null_p_value": null_stacking.p_value,
            "agents_failed": report.metrics["agents_failed"],
        })
    total_points = seed_count * points
    latencies = sorted(float(row["latency_ms"]) for row in rows)
    baseline_names = sorted(rows[0]["baselines"])
    h2_hits = sum(int(row["h2_p_value"] <= PREREGISTRATION["stacking"]["alpha"]) for row in rows)
    h2_null_hits = sum(int(row["h2_null_p_value"] <= PREREGISTRATION["stacking"]["alpha"]) for row in rows)
    summary = {
        "scope": "synthetic_sanity_benchmark_not_external_validation",
        "methodology_version": PREREGISTRATION["methodology_version"],
        "preregistration_sha256": preregistration_hash(),
        "runs": seed_count,
        "points_per_run": points,
        "astra_regime": _aggregate([row["regime"] for row in rows], total_points),
        "astra_anomaly": _aggregate([row["anomaly"] for row in rows], total_points),
        "baselines": {name: _aggregate([row["baselines"][name] for row in rows], total_points) for name in baseline_names},
        "h2_significant_rate_at_preregistered_alpha": h2_hits / seed_count,
        "h2_significant_rate_ci95": wilson_interval(h2_hits, seed_count),
        "h2_false_positive_rate_under_zero_signal": h2_null_hits / seed_count,
        "h2_false_positive_rate_ci95": wilson_interval(h2_null_hits, seed_count),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": latencies[min(len(latencies) - 1, round(0.95 * (len(latencies) - 1)))],
        "agent_failures": sum(int(row["agents_failed"]) for row in rows),
    }
    output = Path("artifacts/reports/benchmark-v0.2-latest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "runs": rows}, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(_benchmark_markdown(summary), encoding="utf-8")
    print("\nBenchmark ASTRA v0.2 concluido")
    print(f"Execucoes: {seed_count}")
    print(f"ASTRA regimes: precision={summary['astra_regime']['precision']:.1%}, recall={summary['astra_regime']['recall']:.1%}, F1={summary['astra_regime']['f1']:.1%}")
    print(f"IC95% recall: {tuple(round(x, 4) for x in summary['astra_regime']['recall_ci95'])}")
    print(f"Falsos alarmes/1.000 pontos: {summary['astra_regime']['false_alarms_per_1000']:.3f}")
    print(f"Atraso absoluto medio: {summary['astra_regime']['mean_absolute_delay']:.2f} pontos")
    print(f"H2: poder no sinal fixo={summary['h2_significant_rate_at_preregistered_alpha']:.1%}; falso positivo sob sinal zero={summary['h2_false_positive_rate_under_zero_signal']:.1%}")
    for name, metric in summary["baselines"].items():
        print(f"{name}: precision={metric['precision']:.1%}, recall={metric['recall']:.1%}, F1={metric['f1']:.1%}")
    print(f"Latencia p95: {summary['latency_p95_ms']:.2f} ms")
    print(f"Falhas de agentes: {summary['agent_failures']}")
    print(f"Detalhes: {output}")


def _benchmark_markdown(summary: dict) -> str:
    rows = [
        "# ASTRA v0.2 - benchmark de sanidade sintetico", "",
        "> Este resultado nao constitui validacao externa.", "",
        "| Metodo | Precision | Recall | F1 | Falsos alarmes/1.000 | Atraso abs. medio |", "|---|---:|---:|---:|---:|---:|",
    ]
    methods = {"ASTRA": summary["astra_regime"], **summary["baselines"]}
    for name, item in methods.items():
        delay = "n/a" if item["mean_absolute_delay"] is None else f"{item['mean_absolute_delay']:.2f}"
        rows.append(f"| {name} | {item['precision']:.1%} | {item['recall']:.1%} | {item['f1']:.1%} | {item['false_alarms_per_1000']:.3f} | {delay} |")
    rows += ["", f"- Runs: {summary['runs']}", f"- Latencia p95: {summary['latency_p95_ms']:.2f} ms", f"- Pre-registro: `{summary['preregistration_sha256']}`", ""]
    rows += [f"- H2: taxa significativa no sinal fixo {summary['h2_significant_rate_at_preregistered_alpha']:.1%} (IC95% {summary['h2_significant_rate_ci95']})", f"- H2: falso positivo sob sinal zero {summary['h2_false_positive_rate_under_zero_signal']:.1%} (IC95% {summary['h2_false_positive_rate_ci95']})", ""]
    return "\n".join(rows)
