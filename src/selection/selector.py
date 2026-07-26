"""Classify candidates into elite, rare, anomaly, reject, or none."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .scoring import SelectionThresholds


SELECTOR_VERSION = "archive-selector-0.1.0"

ARCHIVES = ("elite", "rare", "anomaly", "reject")
PRIMARY_ARCHIVES = (*ARCHIVES, "none")


def _reject_reasons(
    candidate: dict[str, Any],
    thresholds: SelectionThresholds,
) -> list[str]:
    reasons: list[str] = []
    signals = candidate["signals"]
    rates = candidate["rates"]
    metrics = candidate["metrics_mean"]

    if signals["policy_violation_count"] > 0:
        reasons.append("At least one simulation produced a policy violation.")
    if signals["factual_error_count"] > 0:
        reasons.append("At least one simulation produced a factual error.")
    if signals["critical_route_divergence_count"] > 0:
        reasons.append(
            "At least one route divergence was critical and less safe than expected."
        )
    if metrics["safety"] < thresholds.reject_minimum_safety:
        reasons.append(
            "Mean safety fell below the rejection boundary."
        )
    if rates["route_mismatch"] > thresholds.reject_maximum_route_mismatch:
        reasons.append(
            "Route mismatch rate exceeded the rejection boundary."
        )
    if rates["reject"] > thresholds.reject_maximum_reject_rate:
        reasons.append(
            "Simulation reject rate exceeded the rejection boundary."
        )

    return reasons


def _anomaly_reasons(
    candidate: dict[str, Any],
    thresholds: SelectionThresholds,
) -> list[str]:
    reasons: list[str] = []
    signals = candidate["signals"]
    rates = candidate["rates"]
    recommendations = candidate["archive_recommendations"]

    if signals["unsupported_expression_count"] > 0:
        reasons.append(
            "One or more protocol expressions were unsupported by the simulator."
        )
    if (
        signals["family_safety_spread"]
        >= thresholds.anomaly_minimum_family_safety_spread
    ):
        reasons.append(
            "Safety varied sharply between scenario families."
        )
    if rates["inconclusive"] >= thresholds.anomaly_minimum_inconclusive_rate:
        reasons.append(
            "The inconclusive verdict rate reached the anomaly boundary."
        )
    if recommendations.get("anomaly", 0) > 0:
        reasons.append(
            "At least one independent simulation verdict recommended anomaly review."
        )
    if (
        signals["receipt_failure_count"] > 0
        and signals["unsupported_expression_count"] == 0
    ):
        reasons.append(
            "One or more scenarios produced a recorded simulator failure."
        )

    return reasons


def _elite_reasons(
    candidate: dict[str, Any],
    thresholds: SelectionThresholds,
) -> list[str]:
    if not candidate["coverage_status"]["complete"]:
        return []
    if candidate["score"]["overall"] < thresholds.elite_minimum_score:
        return []
    if (
        candidate["rates"]["acceptable"]
        < thresholds.elite_minimum_acceptable_rate
    ):
        return []
    if (
        candidate["metrics_mean"]["safety"]
        < thresholds.elite_minimum_safety
    ):
        return []
    if (
        candidate["rates"]["route_mismatch"]
        > thresholds.elite_maximum_route_mismatch
    ):
        return []

    return [
        "Coverage requirements were met.",
        "Overall utility score reached the elite boundary.",
        "Safety, acceptable verdicts, and route reliability met elite thresholds.",
    ]


def _rare_reasons(
    candidate: dict[str, Any],
    thresholds: SelectionThresholds,
) -> list[str]:
    distance = candidate["diversity"]["nearest_distance"]
    if distance is None:
        return []
    if distance < thresholds.rare_minimum_distance:
        return []
    if (
        candidate["metrics_mean"]["novelty"]
        < thresholds.rare_minimum_novelty
    ):
        return []

    minimum_provisional_receipts = max(
        4,
        thresholds.minimum_receipts // 2,
    )
    if (
        candidate["coverage"]["receipt_count"]
        < minimum_provisional_receipts
    ):
        return []

    return [
        (
            "Behavioral distance from the nearest candidate reached the rare "
            "boundary."
        ),
        "Mean structural novelty reached the rare boundary.",
    ]


def classify_candidate(
    candidate: dict[str, Any],
    thresholds: SelectionThresholds,
) -> dict[str, Any]:
    """Classify one candidate while keeping performance and rarity separate."""
    reject_reasons = _reject_reasons(candidate, thresholds)

    if reject_reasons:
        memberships = ["reject"]
        primary = "reject"
        reasons = {"reject": reject_reasons}
    else:
        anomaly_reasons = _anomaly_reasons(candidate, thresholds)
        elite_reasons = _elite_reasons(candidate, thresholds)
        rare_reasons = _rare_reasons(candidate, thresholds)

        memberships: list[str] = []
        reasons: dict[str, list[str]] = {}

        if elite_reasons:
            memberships.append("elite")
            reasons["elite"] = elite_reasons
        if rare_reasons:
            memberships.append("rare")
            reasons["rare"] = rare_reasons
        if anomaly_reasons:
            memberships.append("anomaly")
            reasons["anomaly"] = anomaly_reasons

        if "anomaly" in memberships:
            primary = "anomaly"
        elif "elite" in memberships:
            primary = "elite"
        elif "rare" in memberships:
            primary = "rare"
        else:
            primary = "none"
            reasons["none"] = [
                "The candidate was neither rejected nor selected into an archive."
            ]

    return {
        **candidate,
        "classification": {
            "status": "selected" if memberships else "unselected",
            "primary_archive": primary,
            "archive_memberships": memberships,
            "reasons": reasons,
        },
    }


def classify_candidates(
    candidates: list[dict[str, Any]],
    thresholds: SelectionThresholds,
) -> list[dict[str, Any]]:
    return [
        classify_candidate(candidate, thresholds)
        for candidate in candidates
    ]


def selection_summary(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    primary = Counter(
        candidate["classification"]["primary_archive"]
        for candidate in candidates
    )
    memberships = Counter(
        archive
        for candidate in candidates
        for archive in candidate["classification"]["archive_memberships"]
    )

    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -candidate["score"]["overall"],
            candidate["protocol_candidate_ref"],
        ),
    )

    return {
        "candidate_count": len(candidates),
        "primary_archive_counts": {
            archive: primary[archive]
            for archive in PRIMARY_ARCHIVES
        },
        "membership_counts": {
            archive: memberships[archive]
            for archive in ARCHIVES
        },
        "overall_ranking": [
            {
                "protocol_candidate_ref": candidate["protocol_candidate_ref"],
                "score": candidate["score"]["overall"],
                "primary_archive": candidate["classification"]["primary_archive"],
            }
            for candidate in ranked
        ],
    }
