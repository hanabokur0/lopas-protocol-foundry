"""Typed errors raised by the selection stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SelectionError(Exception):
    """Base class for selection-stage failures."""


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


class SelectionInputValidationError(SelectionError):
    """Raised when Simulation Receipts fail schema validation."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"{len(issues)} simulation receipt validation issue(s)."
        )


class MixedSimulationRunsError(SelectionError):
    """Raised when receipts from different runs are mixed unintentionally."""

    def __init__(self, run_ids: list[str]) -> None:
        self.run_ids = run_ids
        super().__init__(
            "Multiple simulation run IDs were found: " + ", ".join(run_ids)
        )


class SelectionOutputError(SelectionError):
    """Raised when an internally generated selection document is inconsistent."""
