"""End-to-end Selection-to-PoC Promotion routing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingest.loader import load_records
from src.ingest.validator import ValidationIssue, load_validator, validate_records

from .errors import (
    RoutingCandidateValidationError,
    RoutingPromotionValidationError,
    SelectionDocumentError,
    StageValidationIssue,
)
from .evidence import load_evidence_manifest
from .matcher import match_candidates, validate_selection_document
from .router import ROUTER_VERSION, route_candidate


ROUTING_PIPELINE_VERSION = "routing-pipeline-0.1.0"


@dataclass(frozen=True)
class RoutingResult:
    """Structured result returned by the routing stage."""

    candidates_path: Path
    selection_path: Path
    candidate_schema_path: Path
    promotion_schema_path: Path
    candidates: list[dict[str, Any]]
    selection_document: dict[str, Any]
    promotions: list[dict[str, Any]]

    def stage_receipt(self) -> dict[str, Any]:
        route_counts: dict[str, int] = {}
        eligible_count = 0

        for promotion in self.promotions:
            route = promotion["decision"]["route"]
            route_counts[route] = route_counts.get(route, 0) + 1
            eligible_count += int(promotion["eligibility"]["eligible"])

        return {
            "schema_version": "0.1.0",
            "receipt_type": "routing_run",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "selection_id": self.selection_document["id"],
            "input": {
                "candidates_path": str(self.candidates_path),
                "selection_path": str(self.selection_path),
                "candidate_schema": str(self.candidate_schema_path),
                "promotion_schema": str(self.promotion_schema_path),
            },
            "versions": {
                "pipeline": ROUTING_PIPELINE_VERSION,
                "router": ROUTER_VERSION,
            },
            "counts": {
                "candidates": len(self.candidates),
                "promotions": len(self.promotions),
                "eligible": eligible_count,
            },
            "routes": dict(sorted(route_counts.items())),
            "status": "success",
        }


def default_candidate_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "protocol_candidate.schema.yaml"
    )


def default_promotion_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "poc_promotion.schema.yaml"
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


def _load_selection(path: Path) -> dict[str, Any]:
    records = load_records(path)
    if len(records) != 1:
        raise SelectionDocumentError(
            "Routing expects exactly one Selection Result document."
        )
    return validate_selection_document(records[0])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def run_routing(
    candidates_path: str | Path,
    selection_path: str | Path,
    *,
    evidence_path: str | Path | None = None,
    current_level: int = 1,
    requested_next_level: int = 2,
    decided_at: datetime | None = None,
    recorded_by: str = "lopas-protocol-foundry",
    candidate_schema_path: str | Path | None = None,
    promotion_schema_path: str | Path | None = None,
) -> RoutingResult:
    """Validate inputs, match candidates, route, and validate promotions."""
    if not 0 <= current_level <= 5:
        raise ValueError("current_level must be between 0 and 5.")
    if not 0 <= requested_next_level <= 5:
        raise ValueError("requested_next_level must be between 0 and 5.")
    if not recorded_by.strip():
        raise ValueError("recorded_by must not be empty.")

    candidate_file = Path(candidates_path).resolve()
    selection_file = Path(selection_path).resolve()
    candidate_schema = (
        Path(candidate_schema_path).resolve()
        if candidate_schema_path is not None
        else default_candidate_schema_path().resolve()
    )
    promotion_schema = (
        Path(promotion_schema_path).resolve()
        if promotion_schema_path is not None
        else default_promotion_schema_path().resolve()
    )

    candidates = load_records(candidate_file)
    candidate_validator = load_validator(candidate_schema)
    valid_candidates, _, candidate_issues = validate_records(
        candidates,
        candidate_validator,
    )
    if candidate_issues:
        raise RoutingCandidateValidationError(
            _convert_issues(candidate_issues)
        )

    selection_document = _load_selection(selection_file)
    evidence_map = load_evidence_manifest(evidence_path)
    pairs = match_candidates(valid_candidates, selection_document)

    moment = decided_at or _utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    promotions = [
        route_candidate(
            candidate,
            selection,
            evidence_map.get(candidate["id"]),
            current_level=current_level,
            requested_next_level=requested_next_level,
            decided_at=moment,
            recorded_by=recorded_by,
            selection_id=selection_document["id"],
        )
        for candidate, selection in pairs
    ]

    promotion_validator = load_validator(promotion_schema)
    valid_promotions, _, promotion_issues = validate_records(
        promotions,
        promotion_validator,
    )
    if promotion_issues:
        raise RoutingPromotionValidationError(
            _convert_issues(promotion_issues)
        )

    return RoutingResult(
        candidates_path=candidate_file,
        selection_path=selection_file,
        candidate_schema_path=candidate_schema,
        promotion_schema_path=promotion_schema,
        candidates=valid_candidates,
        selection_document=selection_document,
        promotions=valid_promotions,
    )
