from __future__ import annotations

import asyncio
import json
import time
from uuid import uuid4

from .agents import CausalAgent, FalsificationAgent, GovernanceAgent, GraphAgent, HypothesisAgent, PhysicsAgent, RegimeAgent, SignalAgent
from .baselines import run_all_baselines
from .config import Settings
from .contracts import AgentResult, AgentStatus, InvestigationReport
from .datasets import SyntheticMarket, generate_synthetic_market
from .evaluation import evaluate_detections
from .observability import RunLogger
from .preregistration import PREREGISTRATION, preregistration_hash


class CircuitBreaker:
    def __init__(self, failure_limit: int = 2):
        self.failure_limit = failure_limit
        self.failures: dict[str, int] = {}

    def allow(self, agent_id: str) -> bool:
        return self.failures.get(agent_id, 0) < self.failure_limit

    def record(self, result: AgentResult) -> None:
        if result.status == AgentStatus.FAILED:
            self.failures[result.agent_id] = self.failures.get(result.agent_id, 0) + 1


class OrchestratorAgent:
    agent_id = "orchestrator-agent"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.breaker = CircuitBreaker()
        self.analytical_agents = [SignalAgent(), RegimeAgent(), PhysicsAgent(), GraphAgent(), CausalAgent()]

    async def _run_one(self, agent, data: SyntheticMarket, logger: RunLogger) -> AgentResult:
        if not self.breaker.allow(agent.agent_id):
            return AgentResult(agent_id=agent.agent_id, status=AgentStatus.SKIPPED, summary="Circuit breaker aberto.", evidence_score=0, latency_ms=0)
        last: AgentResult | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                logger.emit("agent_attempt", agent_id=agent.agent_id, attempt=attempt + 1)
                last = await asyncio.wait_for(asyncio.to_thread(agent.execute, data), timeout=self.settings.agent_timeout_seconds)
                self.breaker.record(last)
                return last
            except TimeoutError:
                logger.emit("agent_timeout", agent_id=agent.agent_id, attempt=attempt + 1)
        return last or AgentResult(agent_id=agent.agent_id, status=AgentStatus.FAILED, summary="Timeout apos retries limitados.", evidence_score=0, latency_ms=self.settings.agent_timeout_seconds*1000, error="TimeoutError")

    async def investigate(self, data: SyntheticMarket | None = None) -> InvestigationReport:
        data = data or generate_synthetic_market(self.settings.points, self.settings.seed)
        run_id, correlation_id = str(uuid4()), str(uuid4())
        logger = RunLogger(run_id, correlation_id, self.settings.output_dir)
        started = time.perf_counter()
        logger.emit("investigation_started", dataset_version=data.version, execution_graph="analytics_parallel->hypothesis->falsification->governance")

        analytical_task = asyncio.gather(*(self._run_one(agent, data, logger) for agent in self.analytical_agents))
        baselines_task = asyncio.to_thread(run_all_baselines, data.returns, PREREGISTRATION["baselines"])
        analytical, baseline_results = await asyncio.gather(analytical_task, baselines_task)
        baseline_map = {baseline.name: baseline.change_points for baseline in baseline_results}
        tolerance = max(20, round(len(data.returns) * PREREGISTRATION["evaluation"]["change_tolerance_fraction"]))
        hypothesis_result, hypotheses = HypothesisAgent().execute(analytical)
        falsification_result = FalsificationAgent().execute(hypotheses, analytical, baseline_map, tolerance)
        pre_governance_results = [*analytical, hypothesis_result, falsification_result]
        governance_result, governance = GovernanceAgent().execute(hypotheses, pre_governance_results, self.settings.min_evidence_score)
        all_results = [*pre_governance_results, governance_result]
        failures = [r for r in all_results if r.status == AgentStatus.FAILED]

        cp = next(r for r in analytical if r.agent_id == "regime-agent").findings.get("change_points", [])
        anomalies = next(r for r in analytical if r.agent_id == "signal-agent").findings.get("anomaly_indices", [])
        regime_metrics = evaluate_detections(data.regime_changes, cp, tolerance, len(data.returns))
        anomaly_metrics = evaluate_detections(
            data.anomaly_times, anomalies,
            PREREGISTRATION["evaluation"]["anomaly_tolerance_points"], len(data.returns),
        )
        baseline_evaluation = {
            baseline.name: {
                "change_points": baseline.change_points,
                "parameters": baseline.parameters,
                "notes": baseline.notes,
                "metrics": evaluate_detections(data.regime_changes, baseline.change_points, tolerance, len(data.returns)).to_dict(),
            }
            for baseline in baseline_results
        }
        stacking = next(r for r in analytical if r.agent_id == "causal-agent").findings.get("stacking", {})
        total_ms = (time.perf_counter()-started)*1000
        latencies = sorted(r.latency_ms for r in all_results)
        report = InvestigationReport(
            run_id=run_id, correlation_id=correlation_id, dataset_version=data.version, seed=self.settings.seed,
            methodology_version=PREREGISTRATION["methodology_version"],
            preregistration_sha256=preregistration_hash(),
            agents=all_results, hypotheses=hypotheses, governance=governance,
            metrics={
                "total_latency_ms": round(total_ms, 3),
                "agent_latency_p50_ms": round(_percentile(latencies, 0.50), 3),
                "agent_latency_p95_ms": round(_percentile(latencies, 0.95), 3),
                "agents_completed": sum(r.status == AgentStatus.COMPLETED for r in all_results),
                "agents_failed": len(failures),
                "correlation_id_present": True,
            },
            scientific_evaluation={
                "scope": "synthetic_sanity_test_not_external_validation",
                "dataset": {"watermark": data.watermark, "sha256": data.sha256, "points": len(data.returns), "signal_amplitude": data.signal_amplitude},
                "change_point_tolerance": tolerance,
                "true_regime_changes": list(data.regime_changes),
                "detected_regime_changes": cp,
                "regime_metrics": regime_metrics.to_dict(),
                "true_anomalies": list(data.anomaly_times),
                "detected_anomalies": anomalies,
                "anomaly_metrics": anomaly_metrics.to_dict(),
                "stacking_h2": stacking,
                "baselines": baseline_evaluation,
                "limitations": [
                    "The detector and generator still share design assumptions.",
                    "Wilson intervals quantify finite event counts, not external validity.",
                    "The temporal null supports association testing, not causal identification.",
                ],
            },
        )
        report_dir = self.settings.output_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / f"{run_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        (report_dir / f"{run_id}.md").write_text(render_markdown(report), encoding="utf-8")
        logger.emit("investigation_finished", decision=governance.decision, total_latency_ms=round(total_ms, 3))
        return report


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    position = (len(values)-1)*q
    low, high = int(position), min(int(position)+1, len(values)-1)
    weight = position-low
    return values[low]*(1-weight) + values[high]*weight


def render_markdown(report: InvestigationReport) -> str:
    lines = [
        "# Relatorio ASTRA - POC local", "",
        f"- Run ID: `{report.run_id}`", f"- Dataset: `{report.dataset_version}`",
        f"- Metodologia: `{report.methodology_version}`",
        f"- Pre-registro SHA-256: `{report.preregistration_sha256}`",
        f"- Decisao: **{report.governance.decision.value}**", f"- Motivo: {report.governance.reason}", "",
        "## O que o sistema encontrou", "",
    ]
    for result in report.agents:
        lines.append(f"- **{result.agent_id}:** {result.summary} (evidence score nao calibrado {result.evidence_score:.0%}, {result.latency_ms:.2f} ms)")
    lines += ["", "## Hipoteses, evidencias e contestacao", ""]
    for hypothesis in report.hypotheses:
        lines.append(f"### {hypothesis.hypothesis_id} - {hypothesis.claim}")
        lines.append(f"- Evidence score: {hypothesis.evidence_score:.0%} (heuristico, nao probabilidade)")
        lines.append(f"- Falsificacao: {hypothesis.falsification_status}")
        lines.append(f"- Evidencias exigidas: {', '.join(hypothesis.required_evidence)}")
        lines.append(f"- Contraevidencias: {', '.join(hypothesis.counterevidence) if hypothesis.counterevidence else 'nenhuma registrada'}")
        lines.append("")
    lines += [
        "## Pacote para revisao humana", "",
        "A pessoa revisora recebe a hipotese, evidencia numerica, procedimento de nulo, tentativa de falsificacao, alternativas dos baselines e limitacoes. Para elevar a evidencia de H2, o p-valor de stacking deve ficar abaixo do alpha pre-registrado; para rebaixar H1, nenhum baseline alternativo deve confirmar a transicao dentro da tolerancia. H1 ainda reutiliza o mesmo dataset e, portanto, nao constitui evidencia independente em sentido forte.", "",
        "## Avaliacao contra a verdade sintetica", "", "```json",
        json.dumps(report.scientific_evaluation, indent=2, ensure_ascii=False), "```", "",
        "> Teste de sanidade sintetico, nao validacao externa. Evidence score nao e probabilidade. Revisao humana obrigatoria; nenhuma acao externa e autorizada.", "",
    ]
    return "\n".join(lines)
