"""End-to-end observation ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .loader import load_records
from .validator import ValidationIssue, load_validator, validate_records


@dataclass(frozen=True)
class IngestResult:
    """Structured result returned by the ingest stage."""

    input_path: Path
    schema_path: Path
    total_records: int
    valid_records: list[dict[str, Any]]
    invalid_records: list[dict[str, Any]]
    issues: list[ValidationIssue]

    @property
    def is_valid(self) -> bool:
        return not self.invalid_records

    def receipt(self) -> dict[str, Any]:
        return {
            "schema_version": "0.1.0",
            "receipt_type": "ingest",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "input": {
                "path": str(self.input_path),
                "schema": str(self.schema_path),
            },
            "counts": {
                "total": self.total_records,
                "valid": len(self.valid_records),
                "invalid": len(self.invalid_records),
                "issues": len(self.issues),
            },
            "status": "success" if self.is_valid else "validation_failed",
            "issues": [issue.as_dict() for issue in self.issues],
        }


def default_schema_path() -> Path:
    """Resolve the repository-local observation schema."""
    return Path(__file__).resolve().parents[2] / "schemas" / "observation.schema.yaml"


def ingest_file(
    input_path: str | Path,
    schema_path: str | Path | None = None,
) -> IngestResult:
    """Load and validate all observation records in one file."""
    input_file = Path(input_path).resolve()
    schema_file = (
        Path(schema_path).resolve()
        if schema_path is not None
        else default_schema_path().resolve()
    )

    records = load_records(input_file)
    validator = load_validator(schema_file)
    valid, invalid, issues = validate_records(records, validator)

    return IngestResult(
        input_path=input_file,
        schema_path=schema_file,
        total_records=len(records),
        valid_records=valid,
        invalid_records=invalid,
        issues=issues,
    )


def write_yaml(path: str | Path, value: Any) -> Path:
    """Write deterministic, UTF-8 YAML."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(
            value,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        ),
        encoding="utf-8",
    )
    return output_path
