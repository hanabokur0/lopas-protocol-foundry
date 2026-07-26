"""Match Selection Result entries to Protocol Candidates."""

from __future__ import annotations

from typing import Any

from .errors import CandidateSelectionMismatchError, SelectionDocumentError


REQUIRED_SELECTION_KEYS = {
    "schema_version",
    "id",
    "recorded_at",
    "source_run_ids",
    "thresholds",
    "versions",
    "results",
    "summary",
}

VALID_ARCHIVES = {"elite", "rare", "anomaly", "reject", "none"}


def validate_selection_document(document: Any) -> dict[str, Any]:
    """Validate the stage-local Selection Result contract used by Routing."""
    if not isinstance(document, dict):
        raise SelectionDocumentError(
            "Selection input must be one YAML/JSON object."
        )

    missing = sorted(REQUIRED_SELECTION_KEYS - set(document))
    if missing:
        raise SelectionDocumentError(
            "Selection document is missing keys: " + ", ".join(missing)
        )

    if document["schema_version"] != "0.1.0":
        raise SelectionDocumentError(
            "Unsupported Selection Result schema_version."
        )
    if not isinstance(document["id"], str) or not document["id"].startswith(
        "selection-"
    ):
        raise SelectionDocumentError("Invalid Selection Result ID.")
    if not isinstance(document["results"], list):
        raise SelectionDocumentError("Selection results must be a list.")

    seen: set[str] = set()
    for index, result in enumerate(document["results"]):
        if not isinstance(result, dict):
            raise SelectionDocumentError(
                f"Selection result {index} must be an object."
            )

        candidate_ref = result.get("protocol_candidate_ref")
        if not isinstance(candidate_ref, str) or not candidate_ref.startswith(
            "protocol-"
        ):
            raise SelectionDocumentError(
                f"Selection result {index} has invalid protocol_candidate_ref."
            )
        if candidate_ref in seen:
            raise SelectionDocumentError(
                f"Duplicate Selection result for {candidate_ref}."
            )
        seen.add(candidate_ref)

        classification = result.get("classification")
        if not isinstance(classification, dict):
            raise SelectionDocumentError(
                f"{candidate_ref}: classification is missing."
            )

        primary = classification.get("primary_archive")
        memberships = classification.get("archive_memberships")
        if primary not in VALID_ARCHIVES:
            raise SelectionDocumentError(
                f"{candidate_ref}: invalid primary archive {primary!r}."
            )
        if not isinstance(memberships, list) or any(
            item not in VALID_ARCHIVES - {"none"} for item in memberships
        ):
            raise SelectionDocumentError(
                f"{candidate_ref}: invalid archive memberships."
            )

        coverage = result.get("coverage")
        rates = result.get("rates")
        metrics = result.get("metrics_mean")
        signals = result.get("signals")
        for name, value in (
            ("coverage", coverage),
            ("rates", rates),
            ("metrics_mean", metrics),
            ("signals", signals),
        ):
            if not isinstance(value, dict):
                raise SelectionDocumentError(
                    f"{candidate_ref}: {name} is missing."
                )

        if not isinstance(result.get("receipt_refs"), list):
            raise SelectionDocumentError(
                f"{candidate_ref}: receipt_refs must be a list."
            )

    return document


def match_candidates(
    candidates: list[dict[str, Any]],
    selection_document: dict[str, Any],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return candidate/result pairs in stable candidate-ID order."""
    candidate_map = {candidate["id"]: candidate for candidate in candidates}
    selection_map = {
        result["protocol_candidate_ref"]: result
        for result in selection_document["results"]
    }

    missing_candidates = sorted(set(selection_map) - set(candidate_map))
    missing_selections = sorted(set(candidate_map) - set(selection_map))

    if missing_candidates or missing_selections:
        parts: list[str] = []
        if missing_candidates:
            parts.append(
                "Selection references missing candidates: "
                + ", ".join(missing_candidates)
            )
        if missing_selections:
            parts.append(
                "Candidates missing Selection results: "
                + ", ".join(missing_selections)
            )
        raise CandidateSelectionMismatchError("; ".join(parts))

    return [
        (candidate_map[candidate_ref], selection_map[candidate_ref])
        for candidate_ref in sorted(candidate_map)
    ]
