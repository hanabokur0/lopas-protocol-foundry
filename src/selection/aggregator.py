"""Aggregate Simulation Receipts by Protocol Candidate."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import fmean, pstdev
import re
from typing import Any


AGGREGATOR_VERSION = "selection-aggregator-0.1.0"

METRIC_KEYS = (
    "completion",
    "safety",
    "explainability",
    "human_work_reduction",
    "novelty",
    "confidence",
)

ROUTES = ("AUTO", "REVIEW", "HOLD", "ESCALATE", "DENY")
VERDICTS = (
    "pass",
    "conditional_pass",
    "revise",
    "reject",
    "inconclusive",
)


def _mean(values: list[float]) -> float:
    return round(fmean(values), 4) if values else 0.0


def _stddev(values: list[float]) -> float:
    return round(pstdev(values), 4) if len(values) > 1 else 0.0


def scenario_family(
    protocol_candidate_ref: str,
    scenario_id: str,
) -> str:
    """Recover a scenario archetype from the deterministic scenario ID."""
    candidate_suffix = protocol_candidate_ref.removeprefix("protocol-")
    prefix = f"scenario-{candidate_suffix}-"
    family = scenario_id[len(prefix):] if scenario_id.startswith(prefix) else scenario_id
    return re.sub(r"-v[0-9]+$", "", family)


def _rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _family_profile(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(receipts)
    safety = [receipt["metrics"]["safety"] for receipt in receipts]
    acceptable = sum(
        receipt["verdict"]["status"] in {"pass", "conditional_pass"}
        for receipt in receipts
    )
    return {
        "count": total,
        "acceptable_rate": _rate(acceptable, total),
        "safety_mean": _mean(safety),
        "route_mismatch_rate": _rate(
            sum(not receipt["routing"]["matched"] for receipt in receipts),
            total,
        ),
        "actual_routes": dict(
            sorted(
                Counter(
                    receipt["routing"]["actual"] for receipt in receipts
                ).items()
            )
        ),
    }


def aggregate_candidate(
    protocol_candidate_ref: str,
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate all receipts for one candidate into an inspectable profile."""
    ordered = sorted(
        receipts,
        key=lambda receipt: (
            receipt["scenario"]["id"],
            receipt["id"],
        ),
    )
    total = len(ordered)

    verdict_counts = Counter(
        receipt["verdict"]["status"] for receipt in ordered
    )
    route_counts = Counter(
        receipt["routing"]["actual"] for receipt in ordered
    )
    recommendation_counts = Counter(
        receipt["verdict"]["archive_recommendation"]
        for receipt in ordered
    )

    metrics_mean = {
        key: _mean([receipt["metrics"][key] for receipt in ordered])
        for key in METRIC_KEYS
    }
    metrics_stddev = {
        key: _stddev([receipt["metrics"][key] for receipt in ordered])
        for key in METRIC_KEYS
    }

    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in ordered:
        family = scenario_family(
            protocol_candidate_ref,
            receipt["scenario"]["id"],
        )
        families[family].append(receipt)

    family_profiles = {
        family: _family_profile(family_receipts)
        for family, family_receipts in sorted(families.items())
    }
    family_safety_values = [
        profile["safety_mean"] for profile in family_profiles.values()
    ]
    safety_spread = (
        round(max(family_safety_values) - min(family_safety_values), 4)
        if family_safety_values
        else 0.0
    )

    policy_violation_count = sum(
        receipt["outcome"]["policy_violation"] for receipt in ordered
    )
    factual_error_count = sum(
        receipt["outcome"]["factual_error"] for receipt in ordered
    )
    route_mismatch_count = sum(
        not receipt["routing"]["matched"] for receipt in ordered
    )
    receipt_failure_count = sum(bool(receipt["failures"]) for receipt in ordered)
    unsupported_expression_count = sum(
        failure["code"] == "UNSUPPORTED_EXPRESSION"
        for receipt in ordered
        for failure in receipt["failures"]
    )
    critical_divergence_count = sum(
        divergence["severity"] == "critical"
        for receipt in ordered
        for divergence in receipt["divergences"]
    )
    critical_route_divergence_count = sum(
        divergence["severity"] == "critical"
        and divergence["type"] == "route"
        for receipt in ordered
        for divergence in receipt["divergences"]
    )

    acceptable_count = (
        verdict_counts["pass"] + verdict_counts["conditional_pass"]
    )

    return {
        "protocol_candidate_ref": protocol_candidate_ref,
        "source_run_ids": sorted({receipt["run_id"] for receipt in ordered}),
        "receipt_refs": [receipt["id"] for receipt in ordered],
        "coverage": {
            "receipt_count": total,
            "unique_scenario_count": len(
                {receipt["scenario"]["id"] for receipt in ordered}
            ),
            "scenario_family_count": len(family_profiles),
            "scenario_families": list(family_profiles),
        },
        "rates": {
            "acceptable": _rate(acceptable_count, total),
            "full_pass": _rate(verdict_counts["pass"], total),
            "conditional_pass": _rate(
                verdict_counts["conditional_pass"],
                total,
            ),
            "revise": _rate(verdict_counts["revise"], total),
            "reject": _rate(verdict_counts["reject"], total),
            "inconclusive": _rate(
                verdict_counts["inconclusive"],
                total,
            ),
            "route_mismatch": _rate(route_mismatch_count, total),
            "policy_violation": _rate(policy_violation_count, total),
            "factual_error": _rate(factual_error_count, total),
            "receipt_failure": _rate(receipt_failure_count, total),
        },
        "metrics_mean": metrics_mean,
        "metrics_stddev": metrics_stddev,
        "route_distribution": {
            route: _rate(route_counts[route], total)
            for route in ROUTES
        },
        "verdict_distribution": {
            verdict: verdict_counts[verdict]
            for verdict in VERDICTS
        },
        "archive_recommendations": dict(
            sorted(recommendation_counts.items())
        ),
        "family_profiles": family_profiles,
        "signals": {
            "policy_violation_count": policy_violation_count,
            "factual_error_count": factual_error_count,
            "route_mismatch_count": route_mismatch_count,
            "critical_divergence_count": critical_divergence_count,
            "critical_route_divergence_count": (
                critical_route_divergence_count
            ),
            "unsupported_expression_count": unsupported_expression_count,
            "receipt_failure_count": receipt_failure_count,
            "family_safety_spread": safety_spread,
        },
    }


def aggregate_receipts(
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate receipts into one profile per Protocol Candidate."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        grouped[receipt["protocol_candidate_ref"]].append(receipt)

    return [
        aggregate_candidate(candidate_ref, grouped[candidate_ref])
        for candidate_ref in sorted(grouped)
    ]
