"""End-to-end Proxy-to-Protocol Candidate pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingest.loader import load_records
from src.ingest.validator import ValidationIssue, load_validator, validate_records

from .errors import (
    ProtocolInputValidationError,
    ProtocolOutputValidationError,
    StageValidationIssue,
)
from .generator import GENERATOR_VERSION, generate_candidates, group_proxies
from .templates import PROTOCOL_TEMPLATE_VERSION


@dataclass(frozen=True)
class ProtocolResult:
    """Structured result returned by the protocol stage."""

    input_path: Path
    proxy_schema_path: Path
    protocol_schema_path: Path
    proxies: list[dict[str, Any]]
    candidates: list[dict[str, Any]]

    def receipt(self) -> dict[str, Any]:
        groups = group_proxies(self.proxies)
        candidate_by_cluster = {
            cluster_id: candidate
            for cluster_id, candidate in zip(groups, self.candidates)
        }

        insufficient: list[dict[str, Any]] = []
        for cluster_id, proxies in groups.items():
            candidate = candidate_by_cluster[cluster_id]
            observed_count = len(
                {
                    reference
                    for proxy in proxies
                    for reference in proxy["observation_refs"]
                }
            )
            required_count = candidate["activation"]["required_observations"]
            if observed_count < required_count:
                insufficient.append(
                    {
                        "candidate_id": candidate["id"],
                        "observed": observed_count,
                        "required": required_count,
                    }
                )

        return {
            "schema_version": "0.1.0",
            "receipt_type": "protocol_generation",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "input": {
                "path": str(self.input_path),
                "proxy_schema": str(self.proxy_schema_path),
                "protocol_schema": str(self.protocol_schema_path),
            },
            "generator": {
                "type": "rule",
                "generator_version": GENERATOR_VERSION,
                "template_version": PROTOCOL_TEMPLATE_VERSION,
                "strategy": "one_candidate_per_proxy_cluster",
            },
            "counts": {
                "proxies": len(self.proxies),
                "clusters": len(groups),
                "candidates": len(self.candidates),
            },
            "summary": {
                "all_candidates_unconfirmed": all(
                    candidate["intent"]["status"] == "unconfirmed"
                    for candidate in self.candidates
                ),
                "default_routes": {
                    candidate["id"]: candidate["routing"]["default"]
                    for candidate in self.candidates
                },
                "insufficient_observation_counts": insufficient,
            },
            "status": "success",
        }


def default_proxy_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "proxy.schema.yaml"


def default_protocol_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "protocol_candidate.schema.yaml"
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


def build_protocol_candidates(
    input_path: str | Path,
    proxy_schema_path: str | Path | None = None,
    protocol_schema_path: str | Path | None = None,
) -> ProtocolResult:
    """Load, validate, generate, and validate Protocol Candidates."""
    input_file = Path(input_path).resolve()
    proxy_schema = (
        Path(proxy_schema_path).resolve()
        if proxy_schema_path is not None
        else default_proxy_schema_path().resolve()
    )
    protocol_schema = (
        Path(protocol_schema_path).resolve()
        if protocol_schema_path is not None
        else default_protocol_schema_path().resolve()
    )

    proxies = load_records(input_file)

    proxy_validator = load_validator(proxy_schema)
    valid_proxies, _, input_issues = validate_records(proxies, proxy_validator)
    if input_issues:
        raise ProtocolInputValidationError(_convert_issues(input_issues))

    candidates = generate_candidates(valid_proxies)

    protocol_validator = load_validator(protocol_schema)
    valid_candidates, _, output_issues = validate_records(
        candidates,
        protocol_validator,
    )
    if output_issues:
        raise ProtocolOutputValidationError(_convert_issues(output_issues))

    return ProtocolResult(
        input_path=input_file,
        proxy_schema_path=proxy_schema,
        protocol_schema_path=protocol_schema,
        proxies=valid_proxies,
        candidates=valid_candidates,
    )
