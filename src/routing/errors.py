"""Typed errors raised by the routing stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class RoutingError(Exception):
    """Base class for routing-stage failures."""


@dataclass(frozen=True)
class StageValidationIssue:
    """A normalized schema-validation issue."""

    record_index: int
    record_id: str | None
    path: str
    message: str
    validator: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_index": self.record_index,
            "record_id": self.record_id,
            "path": self.path,
            "message": self.message,
            "validator": self.validator,
        }


class RoutingCandidateValidationError(RoutingError):
    """Raised when Protocol Candidates fail schema validation."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"{len(issues)} protocol candidate validation issue(s)."
        )


class RoutingPromotionValidationError(RoutingError):
    """Raised when generated PoC Promotion records fail schema validation."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"{len(issues)} PoC promotion validation issue(s)."
        )


class SelectionDocumentError(RoutingError):
    """Raised when the stage-local Selection Result contract is invalid."""


class EvidenceManifestError(RoutingError):
    """Raised when the optional evidence manifest is invalid."""


class CandidateSelectionMismatchError(RoutingError):
    """Raised when candidates and selection results cannot be matched."""
