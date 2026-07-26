"""End-to-end Simulation Receipt selection pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from src.ingest.loader import load_records
from src.ingest.validator import ValidationIssue, load_validator, validate_records

from .aggregator import AGGREGATOR_VERSION, aggregate_receipts
from .diversity import DIVERSITY_VERSION, annotate_diversity
from .errors import (
    MixedSimulationRunsError,
    SelectionInputValidationError,
    SelectionOutputError,
    StageValidationIssue,
)
from .scoring import (
    SCORING_VERSION,
    SelectionThresholds,
    score_candidates,
)
from .selector import (
    ARCHIVES,
    PRIMARY_ARCHIVES,
    SELECTOR_VERSION,
    classify_candidates,
    selection_summary,
)


SELECTION_PIPELINE_VERSION = "selection-pipeline-0.1.0"
_SELECTION_ID_PATTERN = re.compile(
    r"^selection-[A-Za-z0-9][A-Za-z0-9._-]*$"
)


@dataclass(frozen=True)
class SelectionResult:
    """Structured result returned by the selection stage."""

    input_path: Path
    receipt_schema_path: Path
    receipts: list[dict[str, Any]]
    document: dict[str, Any]

    def stage_receipt(self) -> dict[str, Any]:
        summary = self.document["summary"]
        return {
            "schema_version": "0.1.0",
            "receipt_type": "selection_run",
            "recorded_at": self.document["recorded_at"],
            "selection_id": self.document["id"],
            "input": {
                "path": str(self.input_path),
                "simulation_receipt_schema": str(self.receipt_schema_path),
            },
            "versions": self.document["versions"],
            "counts": {
                "receipts": len(self.receipts),
                "candidates": summary["candidate_count"],
            },
            "archives": summary["membership_counts"],
            "status": "success",
        }


def default_receipt_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "simulation_receipt.schema.yaml"
    )


def _convert_issues(issues: list[ValidationIssue]) -> list[StageValidationIssue]:
    return [
        StageValidationIssue(
            record_index=issue.record_index,
            record_id=issue.observation_id,
            path=issue.path,
            message=issue.message,
            validator=issue.validator,
        )
        for issue in issues
    ]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_selection_id(run_ids: list[str], moment: datetime) -> str:
    if len(run_ids) == 1:
        return f"selection-{run_ids[0].removeprefix('run-')}"
    return f"selection-{moment.strftime('%Y%m%dT%H%M%SZ')}"


def _validate_document(document: dict[str, Any]) -> None:
    """Check the stage-local Selection Result contract."""
    required = {
        "schema_version",
        "id",
        "recorded_at",
        "source_run_ids",
        "thresholds",
        "versions",
        "results",
        "summary",
    }
    missing = sorted(required - set(document))
    if missing:
        raise SelectionOutputError(
            f"Selection document is missing keys: {', '.join(missing)}"
        )

    if document["schema_version"] != "0.1.0":
        raise SelectionOutputError("Unexpected selection schema_version.")
    if _SELECTION_ID_PATTERN.fullmatch(document["id"]) is None:
        raise SelectionOutputError("Invalid selection result ID.")

    candidate_refs: list[str] = []
    for result in document["results"]:
        candidate_ref = result["protocol_candidate_ref"]
        candidate_refs.append(candidate_ref)

        classification = result["classification"]
        primary = classification["primary_archive"]
        memberships = classification["archive_memberships"]

        if primary not in PRIMARY_ARCHIVES:
            raise SelectionOutputError(
                f"Invalid primary archive {primary!r}."
            )
        if any(archive not in ARCHIVES for archive in memberships):
            raise SelectionOutputError(
                f"Invalid archive membership for {candidate_ref}."
            )
        if primary == "reject" and memberships != ["reject"]:
            raise SelectionOutputError(
                "Rejected candidates cannot remain in other archives."
            )
        if primary != "none" and primary not in memberships:
            raise SelectionOutputError(
                f"Primary archive is absent from memberships for {candidate_ref}."
            )
        if primary == "none" and memberships:
            raise SelectionOutputError(
                f"Unselected candidate {candidate_ref} has archive memberships."
            )

    if len(candidate_refs) != len(set(candidate_refs)):
        raise SelectionOutputError(
            "Duplicate candidate results were generated."
        )


def run_selection(
    input_path: str | Path,
    *,
    thresholds: SelectionThresholds | None = None,
    selection_id: str | None = None,
    recorded_at: datetime | None = None,
    allow_mixed_runs: bool = False,
    receipt_schema_path: str | Path | None = None,
) -> SelectionResult:
    """Validate, aggregate, score, compare, classify, and validate output."""
    input_file = Path(input_path).resolve()
    receipt_schema = (
        Path(receipt_schema_path).resolve()
        if receipt_schema_path is not None
        else default_receipt_schema_path().resolve()
    )
    resolved_thresholds = thresholds or SelectionThresholds()
    resolved_thresholds.validate()

    receipts = load_records(input_file)
    receipt_validator = load_validator(receipt_schema)
    valid_receipts, _, input_issues = validate_records(
        receipts,
        receipt_validator,
    )
    if input_issues:
        raise SelectionInputValidationError(_convert_issues(input_issues))

    run_ids = sorted({receipt["run_id"] for receipt in valid_receipts})
    if len(run_ids) > 1 and not allow_mixed_runs:
        raise MixedSimulationRunsError(run_ids)

    moment = recorded_at or _utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    resolved_id = selection_id or _default_selection_id(run_ids, moment)
    if _SELECTION_ID_PATTERN.fullmatch(resolved_id) is None:
        raise ValueError(
            "selection_id must match "
            "^selection-[A-Za-z0-9][A-Za-z0-9._-]*$"
        )

    aggregates = aggregate_receipts(valid_receipts)
    scored = score_candidates(aggregates, resolved_thresholds)
    diversified = annotate_diversity(scored)
    classified = classify_candidates(
        diversified,
        resolved_thresholds,
    )

    document = {
        "schema_version": "0.1.0",
        "id": resolved_id,
        "recorded_at": _iso(moment),
        "source_run_ids": run_ids,
        "thresholds": resolved_thresholds.as_dict(),
        "versions": {
            "pipeline": SELECTION_PIPELINE_VERSION,
            "aggregator": AGGREGATOR_VERSION,
            "scoring": SCORING_VERSION,
            "diversity": DIVERSITY_VERSION,
            "selector": SELECTOR_VERSION,
        },
        "results": classified,
        "summary": selection_summary(classified),
    }
    _validate_document(document)

    return SelectionResult(
        input_path=input_file,
        receipt_schema_path=receipt_schema,
        receipts=valid_receipts,
        document=document,
    )
