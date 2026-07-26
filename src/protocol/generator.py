"""Generate conservative Protocol Candidate documents from Proxy clusters."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
import re
from typing import Any

from .templates import PROTOCOL_TEMPLATE_VERSION, get_template


GENERATOR_VERSION = "protocol-generator-0.1.0"


IMPACT_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "unknown": 3,
}

REVERSIBILITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "unknown": 3,
}

EVIDENCE_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "sparse": 3,
    "unknown": 4,
}


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug or "unclassified"


def cluster_key(proxy: dict[str, Any]) -> str:
    """Return the declared cluster or a task-based fallback."""
    return proxy["classification"].get("cluster_id") or (
        f"task:{proxy['task']['type']}"
    )


def group_proxies(
    proxies: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group proxies into stable, sorted candidate clusters."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for proxy in proxies:
        grouped[cluster_key(proxy)].append(proxy)

    return {
        key: sorted(value, key=lambda item: item["id"])
        for key, value in sorted(grouped.items())
    }


def _most_conservative(
    values: list[str],
    order: dict[str, int],
) -> str:
    return max(values, key=lambda value: order[value])


def _latest_timestamp(proxies: list[dict[str, Any]]) -> str:
    """Return the latest declared creation timestamp deterministically."""
    timestamps = [proxy["created_at"] for proxy in proxies]
    parsed = [(datetime.fromisoformat(value.replace("Z", "+00:00")), value)
              for value in timestamps]
    return max(parsed, key=lambda item: item[0])[1]


def _task_context(proxies: list[dict[str, Any]]) -> str | None:
    values = [
        proxy["task"].get("context")
        for proxy in proxies
        if proxy["task"].get("context")
    ]
    unique = list(dict.fromkeys(values))
    if not unique:
        return None
    if len(unique) == 1:
        return unique[0]
    return " | ".join(unique[:3])


def _aggregate(proxies: list[dict[str, Any]]) -> dict[str, Any]:
    assessments = [proxy["assessment"] for proxy in proxies]
    observation_refs = sorted(
        {
            reference
            for proxy in proxies
            for reference in proxy["observation_refs"]
        }
    )
    average_confidence = round(
        sum(item["confidence"] for item in assessments) / len(assessments),
        3,
    )

    return {
        "observation_refs": observation_refs,
        "proxy_refs": [proxy["id"] for proxy in proxies],
        "external_impact": _most_conservative(
            [item["external_impact"] for item in assessments],
            IMPACT_ORDER,
        ),
        "reversibility": _most_conservative(
            [item["reversibility"] for item in assessments],
            REVERSIBILITY_ORDER,
        ),
        "weakest_evidence": _most_conservative(
            [item["evidence_density"] for item in assessments],
            EVIDENCE_ORDER,
        ),
        "average_confidence": average_confidence,
        "creative_ownership_signal": any(
            item["creative_ownership_signal"] is True for item in assessments
        ),
        "personal_data_possible": any(
            constraint["type"] == "privacy"
            for proxy in proxies
            for constraint in proxy["constraints"]
        ),
        "hard_constraint_present": any(
            constraint.get("hard") is True
            for proxy in proxies
            for constraint in proxy["constraints"]
        ),
        "high_risk_hint_present": any(
            risk["severity"] == "high"
            for proxy in proxies
            for risk in proxy["risk_hints"]
        ),
        "silent_failure_possible": any(
            risk.get("silent_failure_possible") is True
            for proxy in proxies
            for risk in proxy["risk_hints"]
        ),
    }


def _default_route(aggregate: dict[str, Any], template_specific: bool) -> str:
    if not template_specific:
        return "HOLD"
    if aggregate["hard_constraint_present"]:
        return "HOLD"
    if aggregate["external_impact"] in {"high", "unknown"}:
        return "ESCALATE"
    if aggregate["average_confidence"] < 0.5:
        return "HOLD"
    return "REVIEW"


def _activation(aggregate: dict[str, Any]) -> dict[str, Any]:
    impact = aggregate["external_impact"]

    if impact == "low":
        required_observations = 3
        required_source_diversity = 2
        required_simulations = 20
        minimum_pass_rate = 0.85
    elif impact == "medium":
        required_observations = 5
        required_source_diversity = 3
        required_simulations = 30
        minimum_pass_rate = 0.90
    else:
        required_observations = 8
        required_source_diversity = 4
        required_simulations = 50
        minimum_pass_rate = 0.95

    if aggregate["weakest_evidence"] in {"sparse", "unknown"}:
        required_observations += 2
        required_source_diversity += 1

    return {
        "required_observations": required_observations,
        "required_source_diversity": required_source_diversity,
        "required_simulations": required_simulations,
        "minimum_pass_rate": minimum_pass_rate,
        "human_confirmation": True,
    }


def _extra_routing_rules(aggregate: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    if aggregate["creative_ownership_signal"]:
        rules.append(
            {
                "when": {
                    "expression": "creative_ownership_review_complete != true",
                    "description": "Creative ownership has not been reviewed.",
                    "on_unknown": "HOLD",
                },
                "route": "HOLD",
                "reason": (
                    "Creative ownership requires explicit review before simulation "
                    "or use."
                ),
            }
        )

    if aggregate["high_risk_hint_present"]:
        rules.append(
            {
                "when": {
                    "expression": "high_risk_mitigation_confirmed != true",
                    "description": "A declared high-risk hint remains unmitigated.",
                    "on_unknown": "ESCALATE",
                },
                "route": "ESCALATE",
                "reason": "High-risk source conditions require mitigation evidence.",
            }
        )

    if aggregate["average_confidence"] < 0.5:
        rules.append(
            {
                "when": {
                    "expression": "additional_evidence_available != true",
                    "description": "The candidate has low aggregate confidence.",
                    "on_unknown": "HOLD",
                },
                "route": "HOLD",
                "reason": "Additional evidence is required before simulation.",
            }
        )

    return rules


def generate_candidate(
    cluster_id: str,
    proxies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate one unconfirmed Protocol Candidate from one Proxy cluster."""
    if not proxies:
        raise ValueError("A protocol candidate requires at least one Proxy.")

    task_types = {proxy["task"]["type"] for proxy in proxies}
    if len(task_types) != 1:
        raise ValueError(
            f"Cluster {cluster_id!r} contains multiple task types: "
            f"{sorted(task_types)}"
        )

    task_type = next(iter(task_types))
    template, template_specific = get_template(task_type)
    aggregate = _aggregate(proxies)
    default_route = _default_route(aggregate, template_specific)
    candidate_id = f"protocol-{_slug(cluster_id.removeprefix('task:'))}-baseline"

    personal_data_possible = template["personal_data_possible"]
    if aggregate["personal_data_possible"]:
        personal_data_possible = True

    forbidden_actions = list(
        dict.fromkeys(
            [
                *template["forbidden_actions"],
                "activate_without_promotion",
                "execute_when_required_input_is_unknown",
            ]
        )
    )

    candidate = {
        "schema_version": "0.1.0",
        "id": candidate_id,
        "version": "0.1.0",
        "created_at": _latest_timestamp(proxies),
        "intent": {
            "status": "unconfirmed",
            "requested_by": "lopas-protocol-foundry",
            "confirmation_refs": [],
            "note": (
                "Generated as a candidate only. Simulation and explicit promotion "
                "are required before activation."
            ),
        },
        "task": {
            "type": task_type,
            "context": _task_context(proxies),
            "description": template["description"],
        },
        "proxy_refs": aggregate["proxy_refs"],
        "trigger": deepcopy(template["trigger"]),
        "inputs": deepcopy(template["inputs"]),
        "preconditions": deepcopy(template["preconditions"]),
        "steps": deepcopy(template["steps"]),
        "routing": {
            "default": default_route,
            "rules": [
                *deepcopy(template["routing_rules"]),
                *_extra_routing_rules(aggregate),
            ],
        },
        "stop_conditions": deepcopy(template["stop_conditions"]),
        "outputs": deepcopy(template["outputs"]),
        "failure_handling": {
            "default_route": "HOLD" if default_route != "DENY" else "DENY",
            "retry_limit": 1,
            "record_receipt": True,
            "known_failures": deepcopy(template["known_failures"]),
        },
        "safety": {
            "external_impact": aggregate["external_impact"],
            "reversibility": aggregate["reversibility"],
            "authority_scope": template["authority_scope"],
            "creative_ownership_signal": (
                aggregate["creative_ownership_signal"]
            ),
            "personal_data_possible": personal_data_possible,
            "required_human_review": True,
            "forbidden_actions": forbidden_actions,
        },
        "activation": _activation(aggregate),
        "provenance": {
            "observation_refs": aggregate["observation_refs"],
            "proxy_refs": aggregate["proxy_refs"],
            "generator": "rule",
            "model": None,
            "prompt_version": None,
            "rule_version": (
                f"{GENERATOR_VERSION}+{PROTOCOL_TEMPLATE_VERSION}"
            ),
        },
    }

    return candidate


def generate_candidates(
    proxies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate one Protocol Candidate per Proxy cluster."""
    groups = group_proxies(proxies)
    candidates = [
        generate_candidate(cluster_id, group)
        for cluster_id, group in groups.items()
    ]

    identifiers = [candidate["id"] for candidate in candidates]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Generated duplicate protocol candidate identifiers.")

    return candidates
