"""Typed errors raised by the protocol stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ProtocolError(Exception):
    """Base class for protocol-stage failures."""


@dataclass(frozen=True)
class StageValidationIssue:
    """A normalized validation issue for a stage boundary."""

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


class ProtocolInputValidationError(ProtocolError):
    """Raised when input proxies fail the Proxy schema."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(f"{len(issues)} input proxy validation issue(s).")


class ProtocolOutputValidationError(ProtocolError):
    """Raised when generated candidates fail the Protocol Candidate schema."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"{len(issues)} generated protocol candidate validation issue(s)."
        )
