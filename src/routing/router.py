"""Route selected candidates into PoC Promotion decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .policy import (
    POLICY_VERSION,
    Gate,
    evaluate_gates,
    fixed_eligibility_checks,
)


ROUTER_VERSION = "poc-router-0.1.0"


def _risk_level(candidate: dict[str, Any], selection: dict[str, Any]) -> str:
    impact = candidate["safety"]["external_impact"]
    reversibility = candidate["safety"]["reversibility"]
    route_mismatch = selection["rates"]["route_mismatch"]
    family_spread = selection["signals"]["family_safety_spread"]

    if impact == "high" and reversibility in {"low", "unknown"}:
        return "critical"
    if impact == "high" or reversibility == "low":
        return "high"
    if (
        impact == "medium"
        or reversibility == "unknown"
        or route_mismatch > 0.05
        or family_spread >= 0.20
    ):
        return "medium"
    if impact == "unknown":
        return "unknown"
    return "low"


def _data_sensitivity(candidate: dict[str, Any]) -> str:
    if candidate["safety"]["personal_data_possible"] is True:
        return "medium"
    if candidate["safety"]["personal_data_possible"] is None:
        return "unknown"
    return "low"


def _silent_failure_risk(selection: dict[str, Any]) -> str:
    if selection["signals"]["critical_divergence_count"] > 0:
        return "high"
    if (
        selection["rates"]["route_mismatch"] > 0.05
        or selection["signals"]["family_safety_spread"] >= 0.20
    ):
        return "medium"
    return "low"


def _mitigations(
    candidate: dict[str, Any],
    selection: dict[str, Any],
    gates: list[Gate],
) -> list[str]:
    mitigations: list[str] = []

    if candidate["safety"]["personal_data_possible"] is True:
        mitigations.append(
            "Use redacted or synthetic data until a privacy review is complete."
        )
    if candidate["safety"]["required_human_review"]:
        mitigations.append(
            "Keep the candidate in human-review mode during the next level."
        )
    if candidate["safety"]["reversibility"] in {"low", "unknown"}:
        mitigations.append(
            "Define a containment boundary before any external execution."
        )
    if selection["signals"]["family_safety_spread"] >= 0.20:
        mitigations.append(
            "Investigate scenario families with lower safety before promotion."
        )
    if any(gate.status in {"unmet", "unknown"} for gate in gates):
        mitigations.append(
            "Resolve every blocking promotion condition and attach evidence."
        )

    return list(dict.fromkeys(mitigations))


def _eligibility_reasons(gates: list[Gate]) -> list[str]:
    reasons = [
        (
            f"{gate.id}: {gate.description} "
            f"(status={gate.status})"
        )
        for gate in gates
        if gate.blocking and gate.met is not True
    ]
    if not reasons:
        reasons.append("All blocking promotion conditions were met.")
    return reasons


def _approval_record(
    candidate: dict[str, Any],
    evidence: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    evidence = evidence or {}
    approval = evidence.get("approval")

    if isinstance(approval, dict):
        return [
            {
                "role": "protocol_owner",
                "approver_ref": approval.get("approver_ref"),
                "status": approval.get("status", "requested"),
                "decided_at": approval.get("decided_at"),
                "note": approval.get("note"),
            }
        ]

    return [
        {
            "role": "protocol_owner",
            "approver_ref": None,
            "status": (
                "not_required"
                if not candidate["activation"]["human_confirmation"]
                else "requested"
            ),
            "decided_at": None,
            "note": (
                None
                if candidate["activation"]["human_confirmation"]
                else "Candidate configuration does not require confirmation."
            ),
        }
    ]


def _decision(
    candidate: dict[str, Any],
    selection: dict[str, Any],
    eligible: bool,
    gates: list[Gate],
) -> tuple[str, str, str]:
    intent_status = candidate["intent"]["status"]
    primary = selection["classification"]["primary_archive"]

    if intent_status == "denied":
        return (
            "DENY",
            "The candidate intent was explicitly denied.",
            "reject",
        )
    if intent_status == "rejected" or primary == "reject":
        return (
            "REJECT",
            "The candidate or Selection stage marked the design as rejected.",
            "reject",
        )
    if primary == "anomaly":
        return (
            "REVISE",
            "Anomalous behavior must be investigated before promotion.",
            "anomaly",
        )
    if not eligible:
        unmet = sum(
            gate.blocking and gate.met is not True for gate in gates
        )
        return (
            "HOLD",
            f"{unmet} blocking promotion condition(s) remain unresolved.",
            primary if primary in {"elite", "rare"} else "none",
        )
    if primary in {"elite", "rare"}:
        return (
            "PROMOTE",
            "All blocking gates were met for the requested next level.",
            primary,
        )
    return (
        "HOLD",
        "Selection did not place the candidate in a promotable archive.",
        "none",
    )


def route_candidate(
    candidate: dict[str, Any],
    selection: dict[str, Any],
    evidence: dict[str, Any] | None,
    *,
    current_level: int,
    requested_next_level: int,
    decided_at: datetime,
    recorded_by: str,
    selection_id: str,
) -> dict[str, Any]:
    """Build one schema-valid PoC Promotion decision candidate."""
    gates = evaluate_gates(
        candidate,
        selection,
        evidence,
        current_level=current_level,
        requested_next_level=requested_next_level,
    )
    fixed_checks = fixed_eligibility_checks(
        candidate,
        selection,
        gates,
    )

    all_blocking_met = all(
        gate.met is True for gate in gates if gate.blocking
    )
    eligible = all(fixed_checks.values()) and all_blocking_met

    route, reason, archive = _decision(
        candidate,
        selection,
        eligible,
        gates,
    )

    evidence = evidence or {}
    evidence_refs = list(
        dict.fromkeys(
            [
                selection_id,
                *candidate["provenance"]["observation_refs"],
                *candidate["provenance"]["proxy_refs"],
                *evidence.get("evidence_refs", []),
            ]
        )
    )

    overall_risk = _risk_level(candidate, selection)
    data_sensitivity = _data_sensitivity(candidate)
    silent_failure = _silent_failure_risk(selection)

    if overall_risk == "critical":
        external_impact = "critical"
    else:
        external_impact = candidate["safety"]["external_impact"]

    decision_engine = (
        "hybrid"
        if evidence.get("approval") is not None
        else "rule"
    )

    return {
        "schema_version": "0.1.0",
        "id": f"poc-{candidate['id'].removeprefix('protocol-')}",
        "protocol_candidate_ref": candidate["id"],
        "decided_at": decided_at.astimezone(timezone.utc).isoformat().replace(
            "+00:00",
            "Z",
        ),
        "current_level": current_level,
        "requested_next_level": requested_next_level,
        "simulation_receipt_refs": selection["receipt_refs"],
        "evidence_refs": evidence_refs,
        "eligibility": {
            "eligible": eligible,
            "checks": fixed_checks,
            "reasons": _eligibility_reasons(gates),
        },
        "risk_assessment": {
            "external_impact": external_impact,
            "reversibility": candidate["safety"]["reversibility"],
            "data_sensitivity": data_sensitivity,
            "silent_failure_risk": silent_failure,
            "overall": overall_risk,
            "mitigations": _mitigations(candidate, selection, gates),
        },
        "decision": {
            "route": route,
            "reason": reason,
            "archive": archive,
            "expires_at": None,
        },
        "conditions": [gate.as_condition() for gate in gates],
        "approvals": _approval_record(candidate, evidence),
        "provenance": {
            "decision_engine": decision_engine,
            "decision_engine_version": (
                f"{ROUTER_VERSION}+{POLICY_VERSION}"
            ),
            "recorded_by": recorded_by,
            "rule_refs": [
                ROUTER_VERSION,
                POLICY_VERSION,
                selection_id,
            ],
        },
    }
