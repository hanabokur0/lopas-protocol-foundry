"""Generate conservative, deterministic Proxy documents."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .rules import (
    RULE_VERSION,
    confidence_from_observation,
    creative_ownership_signal,
    generalizability_from_observation,
    novelty_from_observation,
    severity_from_observation,
    task_rule,
)


def proxy_id_for(observation_id: str) -> str:
    """Create a stable proxy identifier from one observation identifier."""
    suffix = observation_id.removeprefix("obs-")
    return f"proxy-{suffix}"


def _evidence_refs(observation: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for reference in observation["evidence"]["references"]:
        value = reference.get("source_id")
        if value and value not in refs:
            refs.append(value)
    return refs


def _constraints(observation: dict[str, Any]) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    source = observation["source"]
    visibility = source["visibility"]

    if visibility in {"confidential", "restricted"}:
        constraints.append(
            {
                "type": "privacy",
                "summary": (
                    f"Source visibility is {visibility}; downstream use must "
                    "respect access and retention controls."
                ),
                "hard": True,
            }
        )
    elif visibility == "internal":
        constraints.append(
            {
                "type": "organizational",
                "summary": "Source material is internal and may not be reusable publicly.",
                "hard": False,
            }
        )

    if source.get("usage_note"):
        constraints.append(
            {
                "type": "policy",
                "summary": f"Source usage note: {source['usage_note']}",
                "hard": None,
            }
        )

    for exclusion in observation.get("exclusions", []):
        constraints.append(
            {
                "type": "other",
                "summary": f"Evidence limitation: {exclusion}",
                "hard": False,
            }
        )

    return constraints


def _risk_hints(
    observation: dict[str, Any],
    external_impact: str,
    ownership_signal: bool,
) -> list[dict[str, Any]]:
    signals = observation["signals"]
    source = observation["source"]
    risks: list[dict[str, Any]] = []

    if signals["contradiction_detected"] is True:
        risks.append(
            {
                "type": "evidence_conflict",
                "summary": "The source observation contains or reports a contradiction.",
                "severity": "high",
                "silent_failure_possible": True,
            }
        )

    if signals["urgency"] == "high":
        risks.append(
            {
                "type": "time_pressure",
                "summary": "High urgency may reduce review quality.",
                "severity": "medium",
                "silent_failure_possible": False,
            }
        )

    if source["visibility"] in {"confidential", "restricted"}:
        risks.append(
            {
                "type": "sensitive_source",
                "summary": "The source may contain access-controlled information.",
                "severity": "high",
                "silent_failure_possible": False,
            }
        )

    if external_impact in {"medium", "high"}:
        risks.append(
            {
                "type": "external_impact",
                "summary": (
                    "A derived protocol may affect a party outside the operator's "
                    "private workspace."
                ),
                "severity": "medium" if external_impact == "medium" else "high",
                "silent_failure_possible": True,
            }
        )

    if ownership_signal:
        risks.append(
            {
                "type": "creative_ownership",
                "summary": (
                    "The observation may involve creative ownership; generation "
                    "must preserve attribution and human control."
                ),
                "severity": "medium",
                "silent_failure_possible": True,
            }
        )

    return risks


def generate_proxy(observation: dict[str, Any]) -> dict[str, Any]:
    """Generate one Proxy document from one validated Observation."""
    task_type = observation["task"]["type"]
    rule = task_rule(task_type)
    evidence_refs = _evidence_refs(observation)
    severity = severity_from_observation(observation)
    ownership_signal = creative_ownership_signal(observation)
    generated_at = observation.get("captured_at") or observation["observed_at"]

    friction = [
        {
            "type": friction_type,
            "summary": summary,
            "severity": severity,
            "evidence_refs": list(evidence_refs),
        }
        for friction_type, summary in rule["friction"]
    ]

    if not friction:
        friction = [
            {
                "type": f"observed_{observation['observation']['type']}",
                "summary": observation["observation"]["summary"],
                "severity": severity,
                "evidence_refs": list(evidence_refs),
            }
        ]

    proposed_effects = [
        {
            "type": effect_type,
            "direction": "positive",
            "summary": summary,
            "measurable": None,
        }
        for effect_type, summary in rule["effects"]
    ]

    if not proposed_effects:
        proposed_effects = [
            {
                "type": "candidate_process_improvement",
                "direction": "unknown",
                "summary": (
                    "A reusable process effect is suggested but not yet established."
                ),
                "measurable": None,
            }
        ]

    interpretation_notes = [
        (
            f"Generated by deterministic baseline rules ({RULE_VERSION}); "
            "the Proxy is an interpretation, not a source fact."
        )
    ]
    interpretation_notes.extend(
        f"Evidence limitation carried forward: {item}"
        for item in observation.get("exclusions", [])
    )

    proxy = {
        "schema_version": "0.1.0",
        "id": proxy_id_for(observation["id"]),
        "created_at": generated_at,
        "observation_refs": [observation["id"]],
        "task": deepcopy(observation["task"]),
        "actors": deepcopy(rule["actors"]),
        "friction": friction,
        "proposed_effects": proposed_effects,
        "classification": {
            "domain": rule["domain"],
            "subdomain": rule["subdomain"],
            "tags": list(
                dict.fromkeys(
                    [
                        *rule["tags"],
                        observation["observation"]["type"].replace("_", "-"),
                    ]
                )
            ),
            "cluster_id": f"task:{task_type}",
        },
        "assessment": {
            "evidence_density": observation["evidence"]["density"],
            "external_impact": rule["external_impact"],
            "reversibility": rule["reversibility"],
            "generalizability": generalizability_from_observation(observation),
            "novelty": novelty_from_observation(observation),
            "interpretation_required": True,
            "creative_ownership_signal": ownership_signal,
            "confidence": confidence_from_observation(observation),
        },
        "constraints": _constraints(observation),
        "risk_hints": _risk_hints(
            observation,
            external_impact=rule["external_impact"],
            ownership_signal=ownership_signal,
        ),
        "interpretation_notes": interpretation_notes,
        "provenance": {
            "generator": "rule",
            "generated_from": [observation["id"]],
            "model": None,
            "prompt_version": None,
            "rule_version": RULE_VERSION,
            "generated_at": generated_at,
        },
    }

    return proxy


def generate_proxies(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate one deterministic Proxy per validated Observation."""
    proxies = [generate_proxy(observation) for observation in observations]

    identifiers = [proxy["id"] for proxy in proxies]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Generated duplicate proxy identifiers.")

    return proxies
