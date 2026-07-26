"""Deterministic promotion-gate policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


POLICY_VERSION = "poc-promotion-policy-0.1.0"


@dataclass(frozen=True)
class Gate:
    """One inspectable promotion-gate result."""

    id: str
    description: str
    met: bool | None
    blocking: bool
    evidence_ref: str | None = None

    @property
    def status(self) -> str:
        if self.met is True:
            return "met"
        if self.met is False:
            return "unmet"
        return "unknown"

    def as_condition(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "blocking": self.blocking,
            "status": self.status,
            "evidence_ref": self.evidence_ref,
        }


def _selection_positive(selection: dict[str, Any]) -> bool:
    memberships = selection["classification"]["archive_memberships"]
    return any(archive in {"elite", "rare"} for archive in memberships)


def evaluate_gates(
    candidate: dict[str, Any],
    selection: dict[str, Any],
    evidence: dict[str, Any] | None,
    *,
    current_level: int,
    requested_next_level: int,
) -> list[Gate]:
    """Evaluate all candidate, simulation, and real-world evidence gates."""
    evidence = evidence or {}
    activation = candidate["activation"]
    selection_rates = selection["rates"]
    coverage = selection["coverage"]

    observation_count = len(
        set(candidate["provenance"]["observation_refs"])
    )
    source_diversity = evidence.get("source_diversity")
    approval = evidence.get("approval")
    approval_status = (
        approval.get("status") if isinstance(approval, dict) else None
    )

    minimum_pass_rate = activation.get("minimum_pass_rate")
    pass_rate_met = (
        True
        if minimum_pass_rate is None
        else selection_rates["acceptable"] >= minimum_pass_rate
    )

    return [
        Gate(
            id="condition-level-sequence",
            description=(
                f"Requested promotion must advance exactly one level "
                f"({current_level} → {current_level + 1})."
            ),
            met=requested_next_level == current_level + 1,
            blocking=True,
        ),
        Gate(
            id="condition-selection-archive",
            description=(
                "Selection must place the candidate in elite or rare, "
                "without reject or anomaly as the primary archive."
            ),
            met=(
                _selection_positive(selection)
                and selection["classification"]["primary_archive"]
                not in {"reject", "anomaly"}
            ),
            blocking=True,
            evidence_ref=selection["protocol_candidate_ref"],
        ),
        Gate(
            id="condition-observation-count",
            description=(
                f"At least {activation['required_observations']} distinct "
                "observations are required."
            ),
            met=observation_count >= activation["required_observations"],
            blocking=True,
        ),
        Gate(
            id="condition-source-diversity",
            description=(
                f"At least {activation['required_source_diversity']} verified "
                "source groups are required."
            ),
            met=(
                None
                if source_diversity is None
                else source_diversity
                >= activation["required_source_diversity"]
            ),
            blocking=True,
            evidence_ref=(
                evidence.get("evidence_refs", [None])[0]
                if evidence.get("evidence_refs")
                else None
            ),
        ),
        Gate(
            id="condition-simulation-count",
            description=(
                f"At least {activation['required_simulations']} Simulation "
                "Receipts are required."
            ),
            met=(
                coverage["receipt_count"]
                >= activation["required_simulations"]
            ),
            blocking=True,
        ),
        Gate(
            id="condition-simulation-pass-rate",
            description=(
                "The acceptable simulation rate must satisfy the candidate's "
                "declared minimum."
            ),
            met=pass_rate_met,
            blocking=True,
        ),
        Gate(
            id="condition-no-critical-divergence",
            description=(
                "No critical route divergence, policy violation, or factual "
                "error may remain."
            ),
            met=(
                selection["signals"]["critical_route_divergence_count"] == 0
                and selection["signals"]["policy_violation_count"] == 0
                and selection["signals"]["factual_error_count"] == 0
            ),
            blocking=True,
        ),
        Gate(
            id="condition-authority-defined",
            description="The candidate authority scope must be explicit.",
            met=candidate["safety"]["authority_scope"] != "unknown",
            blocking=True,
        ),
        Gate(
            id="condition-monitoring-defined",
            description=(
                "Monitoring for the requested real-world validation level "
                "must be defined."
            ),
            met=evidence.get("monitoring_defined"),
            blocking=True,
        ),
        Gate(
            id="condition-rollback-defined",
            description=(
                "Rollback or containment for the requested validation level "
                "must be defined."
            ),
            met=evidence.get("rollback_defined"),
            blocking=True,
        ),
        Gate(
            id="condition-human-approval",
            description=(
                "An authorized protocol owner must approve this promotion."
            ),
            met=approval_status == "approved",
            blocking=True,
            evidence_ref=(
                approval.get("approver_ref")
                if isinstance(approval, dict)
                else None
            ),
        ),
    ]


def fixed_eligibility_checks(
    candidate: dict[str, Any],
    selection: dict[str, Any],
    gates: list[Gate],
) -> dict[str, bool]:
    """Map detailed gates into the fixed PoC Promotion schema."""
    by_id = {gate.id: gate for gate in gates}

    provenance_complete = bool(
        candidate["provenance"]["observation_refs"]
        and candidate["provenance"]["proxy_refs"]
        and selection["receipt_refs"]
    )

    simulation_coverage_sufficient = all(
        by_id[gate_id].met is True
        for gate_id in (
            "condition-simulation-count",
            "condition-simulation-pass-rate",
            "condition-no-critical-divergence",
        )
    )

    return {
        "provenance_complete": provenance_complete,
        "schema_valid": True,
        "simulation_coverage_sufficient": simulation_coverage_sufficient,
        "authority_defined": (
            by_id["condition-authority-defined"].met is True
        ),
        "monitoring_defined": (
            by_id["condition-monitoring-defined"].met is True
        ),
        "rollback_defined": (
            by_id["condition-rollback-defined"].met is True
        ),
        "human_review_satisfied": (
            by_id["condition-human-approval"].met is True
        ),
    }
