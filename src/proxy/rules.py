"""Deterministic baseline rules for observation-to-proxy refinement.

These rules are intentionally conservative. They produce an inspectable
baseline that can later be enriched by an LLM without changing the Proxy
schema boundary.
"""

from __future__ import annotations

from typing import Any


RULE_VERSION = "proxy-rules-0.1.0"


TASK_RULES: dict[str, dict[str, Any]] = {
    "meeting_preparation": {
        "domain": "operations",
        "subdomain": "meetings",
        "tags": ["agenda", "decision-retrieval", "meeting-preparation"],
        "actors": [
            {"role": "meeting organizer", "impact": "operator", "note": None},
            {
                "role": "meeting participants",
                "impact": "affected_party",
                "note": None,
            },
        ],
        "friction": [
            (
                "decision_retrieval",
                "Previous decisions and unresolved items must be retrieved.",
            ),
            (
                "agenda_structure",
                "Meeting inputs must be converted into an inspectable agenda.",
            ),
        ],
        "effects": [
            (
                "preparation_time_reduction",
                "Reduce repetitive meeting-preparation work.",
            ),
            (
                "record_consistency_improvement",
                "Improve continuity between prior decisions and the next meeting.",
            ),
        ],
        "external_impact": "low",
        "reversibility": "high",
    },
    "customer_support": {
        "domain": "service_operations",
        "subdomain": "customer_support",
        "tags": ["customer-support", "validation-gate", "reply-preparation"],
        "actors": [
            {"role": "support operator", "impact": "operator", "note": None},
            {"role": "customer", "impact": "affected_party", "note": None},
        ],
        "friction": [
            (
                "request_completeness",
                "Required information may be missing before reply preparation.",
            ),
            (
                "avoidable_reply_loop",
                "Incomplete requests can create repeated clarification cycles.",
            ),
        ],
        "effects": [
            (
                "reply_loop_reduction",
                "Reduce avoidable clarification exchanges.",
            ),
            (
                "response_consistency_improvement",
                "Apply a consistent pre-draft completeness check.",
            ),
        ],
        "external_impact": "medium",
        "reversibility": "high",
    },
}


EVIDENCE_CONFIDENCE = {
    "high": 0.84,
    "medium": 0.70,
    "low": 0.54,
    "sparse": 0.36,
    "unknown": 0.28,
}


def task_rule(task_type: str) -> dict[str, Any]:
    """Return a task-specific rule or a conservative generic rule."""
    if task_type in TASK_RULES:
        return TASK_RULES[task_type]

    normalized = task_type.replace("_", "-")
    return {
        "domain": "unclassified",
        "subdomain": None,
        "tags": [normalized],
        "actors": [
            {"role": "operator", "impact": "operator", "note": None},
            {"role": "affected party", "impact": "affected_party", "note": None},
        ],
        "friction": [],
        "effects": [],
        "external_impact": "unknown",
        "reversibility": "unknown",
    }


def severity_from_observation(observation: dict[str, Any]) -> str:
    """Estimate friction severity without claiming operational proof."""
    signals = observation["signals"]
    observation_type = observation["observation"]["type"]

    if signals["urgency"] == "high" or signals["contradiction_detected"] is True:
        return "high"
    if signals["repeated"] is True or observation_type in {"failure", "complaint"}:
        return "medium"
    if observation_type in {"success", "proposal", "workaround"}:
        return "low"
    return "unknown"


def generalizability_from_observation(observation: dict[str, Any]) -> str:
    repeated = observation["signals"]["repeated"]
    density = observation["evidence"]["density"]

    if repeated is True and density in {"high", "medium"}:
        return "high"
    if repeated is True or density in {"high", "medium"}:
        return "medium"
    if repeated is False and density in {"low", "sparse"}:
        return "low"
    return "unknown"


def novelty_from_observation(observation: dict[str, Any]) -> str:
    hint = observation["signals"].get("novelty_hint")
    observation_type = observation["observation"]["type"]

    if observation_type == "anomaly" and hint:
        return "high"
    if hint:
        return "medium"
    return "low"


def confidence_from_observation(observation: dict[str, Any]) -> float:
    """Calculate a bounded confidence score from declared evidence signals."""
    evidence = observation["evidence"]
    signals = observation["signals"]

    score = EVIDENCE_CONFIDENCE[evidence["density"]]

    if evidence["directness"] == "direct":
        score += 0.08
    elif evidence["directness"] == "inferred":
        score -= 0.08

    if signals["repeated"] is True:
        score += 0.07
    elif signals["repeated"] is False:
        score -= 0.03

    if signals["contradiction_detected"] is True:
        score -= 0.16

    if observation.get("exclusions"):
        score -= min(0.10, 0.02 * len(observation["exclusions"]))

    return round(max(0.0, min(1.0, score)), 3)


def creative_ownership_signal(observation: dict[str, Any]) -> bool:
    """Flag likely creative-ownership contexts using transparent keywords."""
    text = " ".join(
        [
            observation["task"]["type"],
            observation["task"].get("context") or "",
            observation["task"].get("description") or "",
            observation["observation"]["summary"],
        ]
    ).lower()

    keywords = {
        "author",
        "creative",
        "copyright",
        "design",
        "illustration",
        "music",
        "novel",
        "story",
        "writer",
        "writing",
    }
    return any(keyword in text for keyword in keywords)
