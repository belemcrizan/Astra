from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from scipy.special import gammaln


@dataclass(frozen=True)
class BaselineResult:
    name: str
    change_points: list[int]
    parameters: dict[str, float | int | str]
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


def _robust_standardize(values: np.ndarray) -> np.ndarray:
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return (values - median) / max(1.4826 * mad, 1e-12)


def _volatility_feature(returns: np.ndarray) -> np.ndarray:
    floor = max(float(np.median(returns * returns)), 1e-12)
    return _robust_standardize(np.log(returns * returns + floor))


def cusum_baseline(returns: np.ndarray, drift: float, threshold: float, cooldown: int) -> BaselineResult:
    feature = _volatility_feature(returns)
    positive = negative = 0.0
    points: list[int] = []
    blocked_until = -1
    for index, value in enumerate(feature):
        positive = max(0.0, positive + float(value) - drift)
        negative = min(0.0, negative + float(value) + drift)
        if index >= blocked_until and (positive >= threshold or -negative >= threshold):
            points.append(index)
            positive = negative = 0.0
            blocked_until = index + cooldown
    return BaselineResult("CUSUM-volatility", points, {"drift": drift, "threshold": threshold, "cooldown": cooldown}, "Two-sided CUSUM on robust log-squared returns.")


def page_hinkley_baseline(returns: np.ndarray, delta: float, threshold: float, cooldown: int) -> BaselineResult:
    feature = _volatility_feature(returns)
    points: list[int] = []
    count = 0
    mean = cumulative = 0.0
    minimum = maximum = 0.0
    blocked_until = -1
    for index, value in enumerate(feature):
        count += 1
        mean += (float(value) - mean) / count
        cumulative += float(value) - mean - delta
        minimum = min(minimum, cumulative)
        maximum = max(maximum, cumulative)
        if index >= blocked_until and (cumulative - minimum >= threshold or maximum - cumulative >= threshold):
            points.append(index)
            count, mean, cumulative, minimum, maximum = 0, 0.0, 0.0, 0.0, 0.0
            blocked_until = index + cooldown
    return BaselineResult("Page-Hinkley-volatility", points, {"delta": delta, "threshold": threshold, "cooldown": cooldown}, "Two-sided Page-Hinkley on robust log-squared returns.")


def _gaussian_segment_cost(prefix: np.ndarray, prefix2: np.ndarray, start: np.ndarray, end: int) -> np.ndarray:
    length = end - start
    total = prefix[end] - prefix[start]
    total2 = prefix2[end] - prefix2[start]
    variance = np.maximum((total2 - total * total / length) / length, 1e-12)
    return length * (np.log(variance) + 1.0)


def pelt_baseline(returns: np.ndarray, minimum_segment: int, bic_multiplier: float) -> BaselineResult:
    """PELT: pruned exact optimal partitioning with Gaussian segment cost."""
    values = np.asarray(returns, dtype=float)
    n = len(values)
    penalty = float(bic_multiplier * math.log(n))
    prefix = np.concatenate(([0.0], np.cumsum(values)))
    prefix2 = np.concatenate(([0.0], np.cumsum(values * values)))
    optimum = np.full(n + 1, np.inf)
    optimum[0] = -penalty
    paths: list[list[int]] = [[] for _ in range(n + 1)]
    candidates: list[int] = [0]
    for end in range(minimum_segment, n + 1):
        candidate_array = np.asarray(candidates, dtype=int)
        valid_mask = (end - candidate_array >= minimum_segment) & np.isfinite(optimum[candidate_array])
        valid = candidate_array[valid_mask]
        if valid.size:
            segment_costs = _gaussian_segment_cost(prefix, prefix2, valid, end)
            costs = optimum[valid] + segment_costs + penalty
            winner_position = int(np.argmin(costs))
            winner = int(valid[winner_position])
            optimum[end] = float(costs[winner_position])
            paths[end] = paths[winner] + ([winner] if winner else [])
            keep_invalid = candidate_array[~valid_mask]
            keep_valid = valid[optimum[valid] + segment_costs <= optimum[end]]
            candidates = np.concatenate((keep_invalid, keep_valid)).astype(int).tolist()
        candidates.append(end)
    return BaselineResult("PELT-Gaussian", paths[n], {"minimum_segment": minimum_segment, "bic_multiplier": bic_multiplier, "penalty": penalty}, "Gaussian mean/variance cost with BIC-like penalty.")


def _student_t_logpdf(x: float, mu: np.ndarray, kappa: np.ndarray, alpha: np.ndarray, beta: np.ndarray) -> np.ndarray:
    degrees = 2 * alpha
    scale2 = beta * (kappa + 1) / (alpha * kappa)
    return (
        gammaln((degrees + 1) / 2) - gammaln(degrees / 2)
        - 0.5 * np.log(degrees * math.pi * scale2)
        - ((degrees + 1) / 2) * np.log1p((x - mu) ** 2 / (degrees * scale2))
    )


def bocpd_baseline(returns: np.ndarray, hazard_lambda: int, minimum_mode_drop: int, minimum_separation: int) -> BaselineResult:
    """Adams-MacKay style BOCPD with Normal-Inverse-Gamma observations."""
    values = np.asarray(returns, dtype=float)
    prior_mu = 0.0
    prior_kappa = 0.01
    prior_alpha = 1.0
    prior_beta = max(float(np.var(values)), 1e-8)
    probabilities = np.array([1.0])
    mu = np.array([prior_mu])
    kappa = np.array([prior_kappa])
    alpha = np.array([prior_alpha])
    beta = np.array([prior_beta])
    hazard = 1.0 / hazard_lambda
    scores = np.zeros(len(values))
    previous_mode = 0
    for index, value in enumerate(values):
        log_predictive = _student_t_logpdf(float(value), mu, kappa, alpha, beta)
        log_predictive -= float(np.max(log_predictive))
        predictive = np.exp(log_predictive)
        weighted = probabilities * predictive
        new_probabilities = np.empty(len(probabilities) + 1)
        new_probabilities[0] = hazard * weighted.sum()
        new_probabilities[1:] = (1 - hazard) * weighted
        new_probabilities /= max(new_probabilities.sum(), 1e-300)

        new_kappa_old = kappa + 1
        updated_mu = (kappa * mu + value) / new_kappa_old
        updated_alpha = alpha + 0.5
        updated_beta = beta + 0.5 * kappa * (value - mu) ** 2 / new_kappa_old
        prior_kappa_new = prior_kappa + 1
        prior_mu_new = (prior_kappa * prior_mu + value) / prior_kappa_new
        prior_alpha_new = prior_alpha + 0.5
        prior_beta_new = prior_beta + 0.5 * prior_kappa * (value - prior_mu) ** 2 / prior_kappa_new
        mu = np.concatenate(([prior_mu_new], updated_mu))
        kappa = np.concatenate(([prior_kappa_new], new_kappa_old))
        alpha = np.concatenate(([prior_alpha_new], updated_alpha))
        beta = np.concatenate(([prior_beta_new], updated_beta))
        probabilities = new_probabilities
        mode = int(np.argmax(probabilities))
        scores[index] = max(0, previous_mode + 1 - mode)
        previous_mode = mode
    candidates = np.flatnonzero(scores >= minimum_mode_drop)
    points: list[int] = []
    for index in candidates[np.argsort(scores[candidates])[::-1]]:
        if all(abs(int(index) - existing) >= minimum_separation for existing in points):
            points.append(int(index))
    return BaselineResult("BOCPD-NIG", sorted(points), {"hazard_lambda": hazard_lambda, "minimum_mode_drop": minimum_mode_drop, "minimum_separation": minimum_separation}, "Run-length posterior with Normal-Inverse-Gamma predictive model; detections are MAP run-length collapses.")


def run_all_baselines(returns: np.ndarray, config: dict) -> list[BaselineResult]:
    return [
        cusum_baseline(returns, **config["cusum"]),
        page_hinkley_baseline(returns, **config["page_hinkley"]),
        pelt_baseline(returns, **config["pelt"]),
        bocpd_baseline(returns, **config["bocpd"]),
    ]
