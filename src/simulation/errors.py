"""Typed errors raised by the simulation stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SimulationError(Exception):
    """Base class for simulation-stage failures."""


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


class SimulationInputValidationError(SimulationError):
    """Raised when Protocol Candidates fail schema validation."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"{len(issues)} protocol candidate validation issue(s)."
        )


class SimulationOutputValidationError(SimulationError):
    """Raised when generated Simulation Receipts fail schema validation."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"{len(issues)} simulation receipt validation issue(s)."
        )
