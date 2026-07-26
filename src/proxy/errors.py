"""Typed errors raised by the proxy stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ProxyError(Exception):
    """Base class for proxy-stage failures."""


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


class ProxyInputValidationError(ProxyError):
    """Raised when input observations fail the Observation schema."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(f"{len(issues)} input observation validation issue(s).")


class ProxyOutputValidationError(ProxyError):
    """Raised when generated proxies fail the Proxy schema."""

    def __init__(self, issues: list[StageValidationIssue]) -> None:
        self.issues = issues
        super().__init__(f"{len(issues)} generated proxy validation issue(s).")
