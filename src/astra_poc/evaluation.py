from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class DetectionMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    false_alarms_per_1000: float
    mean_signed_delay: float | None
    mean_absolute_delay: float | None
    matched_pairs: list[tuple[int, int]]
    precision_ci95: tuple[float, float]
    recall_ci95: tuple[float, float]

    def to_dict(self) -> dict:
        return asdict(self)


def _better(first: tuple[int, int], second: tuple[int, int]) -> tuple[int, int]:
    """Maximize matches, then minimize total absolute delay."""
    return first if (first[0], -first[1]) >= (second[0], -second[1]) else second


def match_detections(truth: Iterable[int], predictions: Iterable[int], tolerance: int) -> list[tuple[int, int]]:
    """Order-preserving dynamic program for one-to-one temporal matching."""
    true_points = sorted(set(map(int, truth)))
    predicted_points = sorted(set(map(int, predictions)))
    rows, cols = len(true_points), len(predicted_points)
    score = [[(0, 0) for _ in range(cols + 1)] for _ in range(rows + 1)]
    action = [["" for _ in range(cols + 1)] for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        action[i][0] = "truth"
    for j in range(1, cols + 1):
        action[0][j] = "prediction"
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            best = score[i - 1][j]
            best_action = "truth"
            candidate = score[i][j - 1]
            if _better(candidate, best) == candidate:
                best, best_action = candidate, "prediction"
            delay = abs(predicted_points[j - 1] - true_points[i - 1])
            if delay <= tolerance:
                prior = score[i - 1][j - 1]
                candidate = (prior[0] + 1, prior[1] + delay)
                if _better(candidate, best) == candidate:
                    best, best_action = candidate, "match"
            score[i][j], action[i][j] = best, best_action
    pairs: list[tuple[int, int]] = []
    i, j = rows, cols
    while i or j:
        choice = action[i][j]
        if choice == "match":
            pairs.append((true_points[i - 1], predicted_points[j - 1]))
            i, j = i - 1, j - 1
        elif choice == "truth":
            i -= 1
        else:
            j -= 1
    return list(reversed(pairs))


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    # z=1.959963984540054 for the preregistered 95% interval.
    if confidence != 0.95:
        raise ValueError("This POC preregisters only 95% Wilson intervals.")
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, center - margin), min(1.0, center + margin))


def evaluate_detections(truth: Iterable[int], predictions: Iterable[int], tolerance: int, series_length: int) -> DetectionMetrics:
    true_points = sorted(set(map(int, truth)))
    predicted_points = sorted(set(map(int, predictions)))
    pairs = match_detections(true_points, predicted_points, tolerance)
    tp = len(pairs)
    fp = len(predicted_points) - tp
    fn = len(true_points) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    delays = [prediction - actual for actual, prediction in pairs]
    return DetectionMetrics(
        true_positives=tp, false_positives=fp, false_negatives=fn,
        precision=precision, recall=recall, f1=f1,
        false_alarms_per_1000=1000 * fp / max(series_length, 1),
        mean_signed_delay=float(np.mean(delays)) if delays else None,
        mean_absolute_delay=float(np.mean(np.abs(delays))) if delays else None,
        matched_pairs=pairs,
        precision_ci95=wilson_interval(tp, tp + fp),
        recall_ci95=wilson_interval(tp, tp + fn),
    )


def aggregate_detection_counts(rows: list[dict], prefix: str) -> dict:
    tp = sum(int(row[f"{prefix}_tp"]) for row in rows)
    fp = sum(int(row[f"{prefix}_fp"]) for row in rows)
    fn = sum(int(row[f"{prefix}_fn"]) for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": precision, "precision_ci95": wilson_interval(tp, tp + fp),
        "recall": recall, "recall_ci95": wilson_interval(tp, tp + fn), "f1": f1,
    }

