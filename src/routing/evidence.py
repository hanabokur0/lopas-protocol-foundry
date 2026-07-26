"""Load optional real-world evidence needed by the promotion gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.ingest.loader import load_records

from .errors import EvidenceManifestError


ALLOWED_KEYS = {
    "protocol_candidate_ref",
    "source_diversity",
    "monitoring_defined",
    "rollback_defined",
    "evidence_refs",
    "approval",
}


def _validate_approval(value: Any, candidate_ref: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise EvidenceManifestError(
            f"{candidate_ref}: approval must be an object."
        )

    allowed = {"approver_ref", "status", "decided_at", "note"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise EvidenceManifestError(
            f"{candidate_ref}: unknown approval keys: {', '.join(unknown)}"
        )

    status = value.get("status", "requested")
    if status not in {"requested", "approved", "rejected", "not_required"}:
        raise EvidenceManifestError(
            f"{candidate_ref}: invalid approval status {status!r}."
        )

    return {
        "approver_ref": value.get("approver_ref"),
        "status": status,
        "decided_at": value.get("decided_at"),
        "note": value.get("note"),
    }


def validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Validate one stage-local evidence manifest entry."""
    unknown = sorted(set(entry) - ALLOWED_KEYS)
    if unknown:
        raise EvidenceManifestError(
            "Unknown evidence manifest keys: " + ", ".join(unknown)
        )

    candidate_ref = entry.get("protocol_candidate_ref")
    if not isinstance(candidate_ref, str) or not candidate_ref.startswith(
        "protocol-"
    ):
        raise EvidenceManifestError(
            "Each evidence entry requires protocol_candidate_ref."
        )

    source_diversity = entry.get("source_diversity")
    if source_diversity is not None:
        if not isinstance(source_diversity, int) or source_diversity < 0:
            raise EvidenceManifestError(
                f"{candidate_ref}: source_diversity must be a non-negative integer."
            )

    for key in ("monitoring_defined", "rollback_defined"):
        value = entry.get(key)
        if value is not None and not isinstance(value, bool):
            raise EvidenceManifestError(
                f"{candidate_ref}: {key} must be true, false, or null."
            )

    evidence_refs = entry.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not all(
        isinstance(item, str) and item for item in evidence_refs
    ):
        raise EvidenceManifestError(
            f"{candidate_ref}: evidence_refs must be a list of strings."
        )

    return {
        "protocol_candidate_ref": candidate_ref,
        "source_diversity": source_diversity,
        "monitoring_defined": entry.get("monitoring_defined"),
        "rollback_defined": entry.get("rollback_defined"),
        "evidence_refs": list(dict.fromkeys(evidence_refs)),
        "approval": _validate_approval(
            entry.get("approval"),
            candidate_ref,
        ),
    }


def load_evidence_manifest(
    path: str | Path | None,
) -> dict[str, dict[str, Any]]:
    """Load zero or more evidence entries keyed by candidate reference."""
    if path is None:
        return {}

    entries = load_records(path)
    validated = [validate_entry(entry) for entry in entries]

    result: dict[str, dict[str, Any]] = {}
    for entry in validated:
        candidate_ref = entry["protocol_candidate_ref"]
        if candidate_ref in result:
            raise EvidenceManifestError(
                f"Duplicate evidence entry for {candidate_ref}."
            )
        result[candidate_ref] = entry

    return result
