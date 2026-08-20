from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from .contracts import AgentResult, AgentStatus, Decision, Evidence, GovernanceResult, Hypothesis
from .datasets import SyntheticMarket
from .preregistration import PREREGISTRATION
from .stacking import event_stacking_test


def robust_zscore(values: np.ndarray) -> np.ndarray:
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    scale = max(1.4826 * mad, 1e-12)
    return (values - median) / scale


def normalized_correlation(values: np.ndarray, template: np.ndarray) -> np.ndarray:
    centered = template - template.mean()
    norm = np.linalg.norm(centered)
    if norm == 0 or len(values) < len(template):
        return np.array([], dtype=float)
    windows = np.lib.stride_tricks.sliding_window_view(values, len(template))
    windows = windows - windows.mean(axis=1, keepdims=True)
    denom = np.linalg.norm(windows, axis=1) * norm
    return (windows @ centered) / np.maximum(denom, 1e-12)


class BaseAgent(ABC):
    agent_id: str

    def execute(self, data: SyntheticMarket, context: dict[str, Any] | None = None) -> AgentResult:
        started = time.perf_counter()
        try:
            result = self.analyze(data, context or {})
            result.latency_ms = (time.perf_counter() - started) * 1000
            return result
        except Exception as exc:
            return AgentResult(
                agent_id=self.agent_id, status=AgentStatus.FAILED,
                summary="Falha controlada; o orquestrador pode degradar sem perder a execucao.",
                evidence_score=0.0, latency_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
            )

    @abstractmethod
    def analyze(self, data: SyntheticMarket, context: dict[str, Any]) -> AgentResult: ...


class SignalAgent(BaseAgent):
    agent_id = "signal-agent"

    def analyze(self, data: SyntheticMarket, context: dict[str, Any]) -> AgentResult:
        z = robust_zscore(data.returns)
        config = PREREGISTRATION["signal"]
        anomalies = np.flatnonzero(np.abs(z) >= config["robust_z_threshold"]).tolist()
        corr = normalized_correlation(data.returns, data.template)
        corr_z = robust_zscore(corr)
        candidates = np.flatnonzero(corr_z >= config["matched_candidate_z"])
        peaks: list[int] = []
        for idx in candidates[np.argsort(corr_z[candidates])[::-1]]:
            if all(abs(int(idx) - old) >= len(data.template) * 3 for old in peaks):
                peaks.append(int(idx))
            if len(peaks) == config["maximum_matched_candidates"]:
                break
        event_scores = [float(corr_z[t]) for t in np.flatnonzero(data.event_indicator) if t < len(corr_z)]
        matched_snr = float(np.mean(event_scores) / max(np.std(corr_z), 1e-12))
        evidence_score = float(np.clip(0.35 + 0.08 * len(event_scores) + 0.04 * max(matched_snr, 0), 0, 0.90))
        return AgentResult(
            agent_id=self.agent_id, summary=f"{len(anomalies)} anomalias robustas e {len(peaks)} assinaturas candidatas.",
            evidence_score=evidence_score, latency_ms=0,
            evidence=[
                Evidence(code="ROBUST_Z", statement="Pontos acima do limiar robusto pre-registrado", value=len(anomalies), threshold=config["robust_z_threshold"], passed=bool(anomalies)),
                Evidence(code="MATCHED_SNR", statement="SNR agregado da resposta repetida", value=round(matched_snr, 3), threshold=1.0, passed=matched_snr >= 1.0),
            ],
            findings={"anomaly_indices": anomalies, "matched_peaks": sorted(peaks), "matched_snr": matched_snr, "event_scores": event_scores},
        )


class RegimeAgent(BaseAgent):
    agent_id = "regime-agent"

    def __init__(self):
        config = PREREGISTRATION["regime"]
        self.window = config["window"]
        self.min_separation = config["minimum_separation"]
        self.threshold = config["change_score_threshold"]
        self.maximum_candidates = config["maximum_candidates"]

    def analyze(self, data: SyntheticMarket, context: dict[str, Any]) -> AgentResult:
        x, w = data.returns, self.window
        scores = np.zeros(len(x))
        for i in range(w, len(x) - w):
            left, right = x[i-w:i], x[i:i+w]
            pooled = math.sqrt((left.var() + right.var()) / 2 + 1e-12)
            mean_shift = abs(left.mean() - right.mean()) / pooled
            vol_shift = abs(math.log((right.std() + 1e-12) / (left.std() + 1e-12)))
            scores[i] = mean_shift + 1.8 * vol_shift
        order = np.argsort(scores)[::-1]
        points: list[int] = []
        for idx in order:
            if idx < w or idx >= len(x)-w:
                continue
            if scores[idx] < self.threshold:
                break
            if all(abs(int(idx)-old) >= self.min_separation for old in points):
                points.append(int(idx))
            if len(points) == self.maximum_candidates:
                break
        points.sort()
        strengths = [float(scores[p]) for p in points]
        evidence_score = float(np.clip(0.35 + 0.12 * sum(s >= self.threshold for s in strengths), 0, 0.90))
        return AgentResult(
            agent_id=self.agent_id, summary=f"{len(points)} transicoes de regime candidatas.",
            evidence_score=evidence_score, latency_ms=0,
            evidence=[Evidence(code="CHANGE_SCORE", statement="Maior contraste local de media/volatilidade", value=round(max(strengths, default=0), 3), threshold=self.threshold, passed=max(strengths, default=0) >= self.threshold)],
            findings={"change_points": points, "change_scores": strengths, "window": w},
        )


class PhysicsAgent(BaseAgent):
    agent_id = "physics-agent"

    @staticmethod
    def entropy(values: np.ndarray) -> float:
        hist, _ = np.histogram(values, bins=24)
        probabilities = hist[hist > 0] / hist.sum()
        return float(-(probabilities * np.log(probabilities)).sum())

    def analyze(self, data: SyntheticMarket, context: dict[str, Any]) -> AgentResult:
        x = data.returns
        windows = np.array_split(x, 3)
        entropies = [self.entropy(part) for part in windows]
        susceptibility = [float(np.var(part) * len(part)) for part in windows]
        autocorr = []
        relaxation = []
        for part in windows:
            ac = float(np.corrcoef(part[:-1], part[1:])[0, 1])
            autocorr.append(ac)
            relaxation.append(float(-1 / np.log(abs(ac))) if 0 < abs(ac) < 1 else 0.0)
        peak_ratio = max(susceptibility) / max(min(susceptibility), 1e-12)
        return AgentResult(
            agent_id=self.agent_id, summary="Observaveis fisicos indicam mudanca relevante de flutuacao entre janelas.",
            evidence_score=float(np.clip(0.35 + 0.12 * peak_ratio, 0, 0.88)), latency_ms=0,
            evidence=[Evidence(code="SUSCEPTIBILITY", statement="Razao entre maior e menor susceptibilidade", value=round(peak_ratio, 3), threshold=2.0, passed=peak_ratio >= 2.0)],
            findings={"entropy": entropies, "susceptibility": susceptibility, "lag1_autocorrelation": autocorr, "relaxation_time": relaxation},
        )


class GraphAgent(BaseAgent):
    agent_id = "graph-agent"

    def analyze(self, data: SyntheticMarket, context: dict[str, Any]) -> AgentResult:
        event_times = np.flatnonzero(data.event_indicator)
        z = np.abs(robust_zscore(data.returns))
        anomaly_candidates = np.flatnonzero(z >= 3.0)
        edges = [(int(e), int(a)) for e in event_times for a in anomaly_candidates if 0 <= a-e <= 16]
        coverage = len({e for e, _ in edges}) / max(len(event_times), 1)
        return AgentResult(
            agent_id=self.agent_id,
            summary="Grafo temporal conecta eventos conhecidos a respostas proximas sem inferir intencao.",
            evidence_score=float(0.3 + 0.4 * coverage), latency_ms=0,
            evidence=[Evidence(code="TEMPORAL_EDGES", statement="Eventos ligados a movimentos robustos na janela", value=len(edges), threshold=1, passed=bool(edges))],
            findings={"nodes": int(len(event_times) + len(anomaly_candidates)), "edges": edges, "event_coverage": coverage},
        )


class CausalAgent(BaseAgent):
    agent_id = "causal-agent"

    def analyze(self, data: SyntheticMarket, context: dict[str, Any]) -> AgentResult:
        config = PREREGISTRATION["stacking"]
        stacking = event_stacking_test(
            data.returns, data.event_indicator, data.template,
            permutations=config["permutations"], alpha=config["alpha"], seed=data.seed,
        )
        # Operational ranking relative to the preregistered alpha. It is zero
        # when the statistical criterion fails and is still not a probability.
        score = float(np.clip(1.0 - stacking.p_value / config["alpha"], 0, 0.95))
        return AgentResult(
            agent_id=self.agent_id, status=AgentStatus.COMPLETED,
            summary="Resposta empilhada comparada contra nulo temporal por deslocamentos circulares.",
            evidence_score=score, latency_ms=0,
            evidence=[Evidence(code="STACKING_P_VALUE", statement="p-valor empirico pre-registrado para resposta alinhada", value=round(stacking.p_value, 6), threshold=config["alpha"], passed=stacking.significant)],
            findings={"stacking": stacking.to_dict(), "identification": "association under synthetic temporal null; not a causal claim"},
        )


class HypothesisAgent:
    agent_id = "hypothesis-agent"

    def execute(self, results: list[AgentResult]) -> tuple[AgentResult, list[Hypothesis]]:
        started = time.perf_counter()
        by_id = {item.agent_id: item for item in results}
        hypotheses: list[Hypothesis] = []
        regime = by_id.get("regime-agent")
        physics = by_id.get("physics-agent")
        if regime and regime.status == AgentStatus.COMPLETED:
            evidence_score = (regime.evidence_score + (physics.evidence_score if physics else 0.5)) / 2
            hypotheses.append(Hypothesis(
                hypothesis_id="H1", claim="A serie contem transicoes de regime estatisticamente relevantes.",
                evidence_score=evidence_score, supporting_agents=["regime-agent", "physics-agent"],
                required_evidence=["change score acima do limiar", "mudanca de susceptibilidade"],
            ))
        signal = by_id.get("signal-agent")
        causal = by_id.get("causal-agent")
        if signal and signal.status == AgentStatus.COMPLETED:
            evidence_score = (signal.evidence_score + (causal.evidence_score if causal else 0.4)) / 2
            hypotheses.append(Hypothesis(
                hypothesis_id="H2", claim="Eventos repetidos precedem uma assinatura fraca de resposta.",
                evidence_score=evidence_score, supporting_agents=["signal-agent", "causal-agent", "graph-agent"],
                required_evidence=["stacking alinhado", "nulo temporal circular", "p-valor empirico pre-registrado"],
            ))
        hypotheses.sort(key=lambda item: item.evidence_score, reverse=True)
        result = AgentResult(
            agent_id=self.agent_id, summary=f"{len(hypotheses)} hipoteses tipadas geradas.",
            evidence_score=max((h.evidence_score for h in hypotheses), default=0),
            latency_ms=(time.perf_counter()-started)*1000,
            evidence=[Evidence(code="HYPOTHESIS_COUNT", statement="Hipoteses testaveis geradas", value=len(hypotheses), threshold=1, passed=bool(hypotheses))],
            findings={"ranking": [h.hypothesis_id for h in hypotheses]},
        )
        return result, hypotheses


class FalsificationAgent:
    agent_id = "falsification-agent"

    def execute(self, hypotheses: list[Hypothesis], results: list[AgentResult], baselines: dict[str, list[int]], tolerance: int) -> AgentResult:
        started = time.perf_counter()
        by_id = {item.agent_id: item for item in results}
        passed = 0
        for hypothesis in hypotheses:
            if hypothesis.hypothesis_id == "H1":
                regime = by_id["regime-agent"]
                scores = regime.findings.get("change_scores", [])
                astra_points = regime.findings.get("change_points", [])
                pelt_points = baselines.get("PELT-Gaussian", [])
                agreement = sum(any(abs(point - baseline) <= tolerance for baseline in pelt_points) for point in astra_points)
                ok = len(scores) >= 1 and agreement >= 1
                if not ok:
                    hypothesis.counterevidence.append("O detector independente PELT nao confirmou uma transicao dentro da tolerancia.")
            else:
                causal = by_id["causal-agent"]
                stacking = causal.findings.get("stacking", {})
                ok = bool(stacking.get("significant", False))
                if not ok:
                    hypothesis.counterevidence.append("O stacking nao superou o nulo temporal no alpha pre-registrado.")
            hypothesis.falsification_status = "passed" if ok else "challenged"
            passed += int(ok)
        evidence_score = passed / max(len(hypotheses), 1)
        return AgentResult(
            agent_id=self.agent_id,
            summary=f"{passed}/{len(hypotheses)} hipoteses sobreviveram ao procedimento alternativo de contestacao.",
            evidence_score=evidence_score, latency_ms=(time.perf_counter()-started)*1000,
            evidence=[Evidence(code="FALSIFICATION", statement="Hipoteses que passaram criterios adversariais", value=passed, threshold=len(hypotheses), passed=passed == len(hypotheses))],
            findings={"passed": passed, "total": len(hypotheses)},
        )


class GovernanceAgent:
    agent_id = "governance-agent"

    def execute(self, hypotheses: list[Hypothesis], results: list[AgentResult], min_evidence_score: float) -> tuple[AgentResult, GovernanceResult]:
        started = time.perf_counter()
        failures = [result for result in results if result.status == AgentStatus.FAILED]
        accepted = [hypothesis for hypothesis in hypotheses if hypothesis.falsification_status == "passed" and hypothesis.evidence_score >= min_evidence_score]
        if failures:
            decision, reason = Decision.HUMAN_REVIEW, "Execucao degradada: ao menos um agente falhou."
        elif accepted:
            decision, reason = Decision.HUMAN_REVIEW, "Ha evidencias suficientes para revisao humana, nunca para acao automatica."
        else:
            decision, reason = Decision.INSUFFICIENT_EVIDENCE, "Nenhuma hipotese superou confianca e falsificacao."
        governance = GovernanceResult(decision=decision, reason=reason)
        result = AgentResult(
            agent_id=self.agent_id,
            summary=f"Gate concluido em modo passivo: {decision.value}.",
            evidence_score=1.0, latency_ms=(time.perf_counter()-started)*1000,
            evidence=[
                Evidence(code="PASSIVE_MODE", statement="Nenhuma acao externa esta habilitada", value=True, threshold=True, passed=True),
                Evidence(code="HUMAN_GATE", statement="Revisao humana permanece obrigatoria", value=True, threshold=True, passed=True),
            ],
            findings={"accepted_hypotheses": [hypothesis.hypothesis_id for hypothesis in accepted], "decision": decision.value},
        )
        return result, governance
