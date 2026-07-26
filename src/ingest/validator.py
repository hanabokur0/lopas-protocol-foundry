"""Validate observation records against the core JSON Schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .errors import SchemaLoadError


@dataclass(frozen=True)
class ValidationIssue:
    """One schema validation issue attached to one input record."""

    record_index: int
    observation_id: str | None
    path: str
    message: str
    validator: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_index": self.record_index,
            "observation_id": self.observation_id,
            "path": self.path,
            "message": self.message,
            "validator": self.validator,
        }


def load_validator(schema_path: str | Path) -> Draft202012Validator:
    """Load and check a Draft 2020-12 JSON Schema stored as YAML."""
    path = Path(schema_path)

    try:
        schema = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SchemaLoadError(f"Could not read schema {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise SchemaLoadError(f"Invalid YAML schema {path}: {exc}") from exc

    if not isinstance(schema, dict):
        raise SchemaLoadError(f"Schema {path} must contain a YAML object.")

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise SchemaLoadError(f"Invalid JSON Schema {path}: {exc.message}") from exc

    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_records(
    records: list[dict[str, Any]],
    validator: Draft202012Validator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[ValidationIssue]]:
    """Return valid records, invalid records, and normalized issues."""
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    issues: list[ValidationIssue] = []

    for index, record in enumerate(records):
        record_errors = sorted(
            validator.iter_errors(record),
            key=lambda error: [str(part) for part in error.absolute_path],
        )

        if not record_errors:
            valid.append(record)
            continue

        invalid.append(record)
        observation_id = record.get("id") if isinstance(record.get("id"), str) else None

        for error in record_errors:
            path = "$"
            for part in error.absolute_path:
                if isinstance(part, int):
                    path += f"[{part}]"
                else:
                    path += f".{part}"

            issues.append(
                ValidationIssue(
                    record_index=index,
                    observation_id=observation_id,
                    path=path,
                    message=error.message,
                    validator=error.validator,
                )
            )

    return valid, invalid, issues
