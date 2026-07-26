"""Calculate deterministic behavioral distance between candidates."""

from __future__ import annotations

from math import sqrt
from typing import Any


DIVERSITY_VERSION = "behavioral-diversity-0.1.0"

VECTOR_KEYS = (
    "completion",
    "safety",
    "explainability",
    "human_work_reduction",
    "novelty",
    "route_mismatch",
    "receipt_failure",
    "route_auto",
    "route_review",
    "route_hold",
    "route_escalate",
    "route_deny",
)


def behavior_vector(candidate: dict[str, Any]) -> dict[str, float]:
    """Create a bounded vector from simulation behavior only."""
    metrics = candidate["metrics_mean"]
    rates = candidate["rates"]
    routes = candidate["route_distribution"]

    return {
        "completion": metrics["completion"],
        "safety": metrics["safety"],
        "explainability": metrics["explainability"],
        "human_work_reduction": metrics["human_work_reduction"],
        "novelty": metrics["novelty"],
        "route_mismatch": rates["route_mismatch"],
        "receipt_failure": rates["receipt_failure"],
        "route_auto": routes["AUTO"],
        "route_review": routes["REVIEW"],
        "route_hold": routes["HOLD"],
        "route_escalate": routes["ESCALATE"],
        "route_deny": routes["DENY"],
    }


def normalized_euclidean(
    first: dict[str, float],
    second: dict[str, float],
) -> float:
    """Return Euclidean distance normalized to the unit interval."""
    squared = sum(
        (first[key] - second[key]) ** 2
        for key in VECTOR_KEYS
    )
    return round(sqrt(squared / len(VECTOR_KEYS)), 4)


def annotate_diversity(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach each candidate's nearest behavioral neighbor."""
    vectors = {
        candidate["protocol_candidate_ref"]: behavior_vector(candidate)
        for candidate in candidates
    }

    annotated: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_ref = candidate["protocol_candidate_ref"]
        distances = [
            {
                "protocol_candidate_ref": other_ref,
                "distance": normalized_euclidean(
                    vectors[candidate_ref],
                    vectors[other_ref],
                ),
            }
            for other_ref in sorted(vectors)
            if other_ref != candidate_ref
        ]
        distances.sort(
            key=lambda item: (
                item["distance"],
                item["protocol_candidate_ref"],
            )
        )
        nearest = distances[0] if distances else None

        annotated.append(
            {
                **candidate,
                "behavior_vector": vectors[candidate_ref],
                "diversity": {
                    "nearest_neighbor": (
                        nearest["protocol_candidate_ref"]
                        if nearest
                        else None
                    ),
                    "nearest_distance": (
                        nearest["distance"] if nearest else None
                    ),
                    "pairwise_distances": distances,
                },
            }
        )

    return annotated
