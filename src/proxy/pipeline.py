"""End-to-end Observation-to-Proxy pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingest.loader import load_records
from src.ingest.pipeline import write_yaml
from src.ingest.validator import ValidationIssue, load_validator, validate_records

from .errors import (
    ProxyInputValidationError,
    ProxyOutputValidationError,
    StageValidationIssue,
)
from .generator import RULE_VERSION, generate_proxies


@dataclass(frozen=True)
class ProxyResult:
    """Structured result returned by the proxy stage."""

    input_path: Path
    observation_schema_path: Path
    proxy_schema_path: Path
    observations: list[dict[str, Any]]
    proxies: list[dict[str, Any]]

    def receipt(self) -> dict[str, Any]:
        confidence_values = [
            proxy["assessment"]["confidence"] for proxy in self.proxies
        ]
        average_confidence = (
            round(sum(confidence_values) / len(confidence_values), 3)
            if confidence_values
            else None
        )

        return {
            "schema_version": "0.1.0",
            "receipt_type": "proxy_generation",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "input": {
                "path": str(self.input_path),
                "observation_schema": str(self.observation_schema_path),
                "proxy_schema": str(self.proxy_schema_path),
            },
            "generator": {
                "type": "rule",
                "rule_version": RULE_VERSION,
                "strategy": "one_proxy_per_observation",
            },
            "counts": {
                "observations": len(self.observations),
                "proxies": len(self.proxies),
            },
            "summary": {
                "average_confidence": average_confidence,
                "low_confidence_proxies": [
                    proxy["id"]
                    for proxy in self.proxies
                    if proxy["assessment"]["confidence"] < 0.5
                ],
                "creative_ownership_signals": [
                    proxy["id"]
                    for proxy in self.proxies
                    if proxy["assessment"]["creative_ownership_signal"] is True
                ],
            },
            "status": "success",
        }


def default_observation_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "observation.schema.yaml"
    )


def default_proxy_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "proxy.schema.yaml"


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


def build_proxies(
    input_path: str | Path,
    observation_schema_path: str | Path | None = None,
    proxy_schema_path: str | Path | None = None,
) -> ProxyResult:
    """Load, validate, refine, and validate Proxy documents."""
    input_file = Path(input_path).resolve()
    observation_schema = (
        Path(observation_schema_path).resolve()
        if observation_schema_path is not None
        else default_observation_schema_path().resolve()
    )
    proxy_schema = (
        Path(proxy_schema_path).resolve()
        if proxy_schema_path is not None
        else default_proxy_schema_path().resolve()
    )

    observations = load_records(input_file)

    observation_validator = load_validator(observation_schema)
    valid_observations, _, input_issues = validate_records(
        observations,
        observation_validator,
    )
    if input_issues:
        raise ProxyInputValidationError(_convert_issues(input_issues))

    proxies = generate_proxies(valid_observations)

    proxy_validator = load_validator(proxy_schema)
    valid_proxies, _, output_issues = validate_records(proxies, proxy_validator)
    if output_issues:
        raise ProxyOutputValidationError(_convert_issues(output_issues))

    return ProxyResult(
        input_path=input_file,
        observation_schema_path=observation_schema,
        proxy_schema_path=proxy_schema,
        observations=valid_observations,
        proxies=valid_proxies,
    )


__all__ = [
    "ProxyResult",
    "build_proxies",
    "default_observation_schema_path",
    "default_proxy_schema_path",
    "write_yaml",
]
