"""Score candidate aggregates without collapsing safety into one number."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


SCORING_VERSION = "selection-scoring-0.1.0"


@dataclass(frozen=True)
class SelectionThresholds:
    """Deterministic thresholds used by scoring and classification."""

    minimum_receipts: int = 12
    minimum_scenario_families: int = 6

    elite_minimum_score: float = 0.84
    elite_minimum_acceptable_rate: float = 0.90
    elite_minimum_safety: float = 0.90
    elite_maximum_route_mismatch: float = 0.05

    rare_minimum_distance: float = 0.18
    rare_minimum_novelty: float = 0.25

    anomaly_minimum_family_safety_spread: float = 0.30
    anomaly_minimum_inconclusive_rate: float = 0.10

    reject_minimum_safety: float = 0.70
    reject_maximum_route_mismatch: float = 0.25
    reject_maximum_reject_rate: float = 0.20

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> None:
        if self.minimum_receipts < 1:
            raise ValueError("minimum_receipts must be at least 1.")
        if self.minimum_scenario_families < 1:
            raise ValueError(
                "minimum_scenario_families must be at least 1."
            )

        for key, value in self.as_dict().items():
            if key.startswith("minimum_") and key in {
                "minimum_receipts",
                "minimum_scenario_families",
            }:
                continue
            if not 0 <= value <= 1:
                raise ValueError(f"{key} must be between 0 and 1.")


def _coverage_score(
    aggregate: dict[str, Any],
    thresholds: SelectionThresholds,
) -> tuple[float, bool]:
    receipt_ratio = min(
        1.0,
        aggregate["coverage"]["receipt_count"]
        / thresholds.minimum_receipts,
    )
    family_ratio = min(
        1.0,
        aggregate["coverage"]["scenario_family_count"]
        / thresholds.minimum_scenario_families,
    )
    score = round(0.5 * receipt_ratio + 0.5 * family_ratio, 4)
    complete = receipt_ratio >= 1 and family_ratio >= 1
    return score, complete


def score_candidate(
    aggregate: dict[str, Any],
    thresholds: SelectionThresholds,
) -> dict[str, Any]:
    """Calculate a bounded utility score plus explicit component scores."""
    coverage_score, coverage_complete = _coverage_score(
        aggregate,
        thresholds,
    )
    metrics = aggregate["metrics_mean"]
    rates = aggregate["rates"]

    route_reliability = round(1 - rates["route_mismatch"], 4)

    components = {
        "safety": metrics["safety"],
        "acceptable": rates["acceptable"],
        "explainability": metrics["explainability"],
        "route_reliability": route_reliability,
        "confidence": metrics["confidence"],
        "human_work_reduction": metrics["human_work_reduction"],
        "coverage": coverage_score,
    }

    weights = {
        "safety": 0.30,
        "acceptable": 0.20,
        "explainability": 0.12,
        "route_reliability": 0.15,
        "confidence": 0.08,
        "human_work_reduction": 0.10,
        "coverage": 0.05,
    }

    overall = round(
        sum(components[key] * weights[key] for key in weights),
        4,
    )

    return {
        **aggregate,
        "score": {
            "overall": overall,
            "components": components,
            "weights": weights,
        },
        "coverage_status": {
            "complete": coverage_complete,
            "receipt_requirement_met": (
                aggregate["coverage"]["receipt_count"]
                >= thresholds.minimum_receipts
            ),
            "family_requirement_met": (
                aggregate["coverage"]["scenario_family_count"]
                >= thresholds.minimum_scenario_families
            ),
        },
    }


def score_candidates(
    aggregates: list[dict[str, Any]],
    thresholds: SelectionThresholds,
) -> list[dict[str, Any]]:
    thresholds.validate()
    return [
        score_candidate(aggregate, thresholds)
        for aggregate in aggregates
    ]
