"""End-to-end Protocol Candidate simulation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any

from src.ingest.loader import load_records
from src.ingest.validator import ValidationIssue, load_validator, validate_records

from .engine import SIMULATOR_VERSION, simulate_case
from .errors import (
    SimulationInputValidationError,
    SimulationOutputValidationError,
    StageValidationIssue,
)
from .expressions import EXPRESSION_EVALUATOR_VERSION
from .grader import GRADER_VERSION, grade
from .scenarios import (
    SCENARIO_GENERATOR_VERSION,
    ScenarioCase,
    generate_suite,
)


RUN_ID_PATTERN = re.compile(r"^run-[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class SimulationResult:
    """Structured result returned by the simulation stage."""

    input_path: Path
    protocol_schema_path: Path
    receipt_schema_path: Path
    run_id: str
    candidates: list[dict[str, Any]]
    cases: list[ScenarioCase]
    receipts: list[dict[str, Any]]

    def stage_receipt(self) -> dict[str, Any]:
        archetypes = sorted({case.archetype for case in self.cases})
        verdict_counts: dict[str, int] = {}
        route_mismatches = 0

        for receipt in self.receipts:
            status = receipt["verdict"]["status"]
            verdict_counts[status] = verdict_counts.get(status, 0) + 1
            if not receipt["routing"]["matched"]:
                route_mismatches += 1

        return {
            "schema_version": "0.1.0",
            "receipt_type": "simulation_run",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "input": {
                "path": str(self.input_path),
                "protocol_schema": str(self.protocol_schema_path),
                "simulation_receipt_schema": str(self.receipt_schema_path),
            },
            "versions": {
                "scenario_generator": SCENARIO_GENERATOR_VERSION,
                "expression_evaluator": EXPRESSION_EVALUATOR_VERSION,
                "simulator": SIMULATOR_VERSION,
                "grader": GRADER_VERSION,
            },
            "counts": {
                "candidates": len(self.candidates),
                "scenarios": len(self.cases),
                "receipts": len(self.receipts),
                "archetypes": len(archetypes),
                "route_mismatches": route_mismatches,
            },
            "summary": {
                "archetypes": archetypes,
                "verdicts": verdict_counts,
                "simulation_is_not_real_world_validation": True,
            },
            "status": "success",
        }


def default_protocol_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "protocol_candidate.schema.yaml"
    )


def default_receipt_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "simulation_receipt.schema.yaml"
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _run_id(moment: datetime) -> str:
    return f"run-{moment.strftime('%Y%m%dT%H%M%SZ')}"


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _receipt_id(candidate_id: str, scenario_id: str) -> str:
    candidate = candidate_id.removeprefix("protocol-")
    scenario = scenario_id.removeprefix("scenario-")
    return f"simrcpt-{candidate}-{scenario}"


def _build_receipt(
    candidate: dict[str, Any],
    case: ScenarioCase,
    run_id: str,
    moment: datetime,
) -> dict[str, Any]:
    result = simulate_case(candidate, case)
    grading = grade(candidate, case, result)

    output_summary = (
        f"Route {result.actual_route}. "
        f"Task completed: {str(result.task_completed).lower()}. "
        f"{result.route_reason}"
    )

    return {
        "schema_version": "0.1.0",
        "id": _receipt_id(candidate["id"], case.scenario["id"]),
        "run_id": run_id,
        "protocol_candidate_ref": candidate["id"],
        "scenario": case.scenario,
        "simulator": {
            "type": "deterministic",
            "name": "lopas-protocol-foundry-simulator",
            "version": SIMULATOR_VERSION,
            "model": None,
            "prompt_version": None,
        },
        "started_at": _iso(moment),
        "ended_at": _iso(moment + timedelta(milliseconds=1)),
        "outcome": {
            "task_completed": result.task_completed,
            "factual_error": result.factual_error,
            "policy_violation": result.policy_violation,
            "escalation_required": case.expected_route == "ESCALATE",
            "escalation_detected": result.actual_route == "ESCALATE",
            "receipt_complete": result.receipt_complete,
            "output_summary": output_summary,
        },
        "metrics": grading["metrics"],
        "routing": grading["routing"],
        "divergences": grading["divergences"],
        "failures": grading["failures"],
        "grader": {
            "type": "deterministic",
            "name": "lopas-independent-route-grader",
            "independent": True,
            "version": GRADER_VERSION,
            "model": None,
            "notes": (
                "Expected routes are declared by scenario archetypes rather "
                "than copied from simulator output."
            ),
        },
        "verdict": grading["verdict"],
        "provenance": {
            "protocol_version": candidate["version"],
            "scenario_generator_version": SCENARIO_GENERATOR_VERSION,
            "environment_version": (
                f"{SIMULATOR_VERSION}+{EXPRESSION_EVALUATOR_VERSION}"
            ),
            "recorded_at": _iso(moment + timedelta(milliseconds=1)),
        },
    }


def run_simulation(
    input_path: str | Path,
    *,
    scenario_count: int | None = None,
    run_id: str | None = None,
    recorded_at: datetime | None = None,
    protocol_schema_path: str | Path | None = None,
    receipt_schema_path: str | Path | None = None,
) -> SimulationResult:
    """Validate candidates, generate scenarios, simulate, grade, and validate."""
    input_file = Path(input_path).resolve()
    protocol_schema = (
        Path(protocol_schema_path).resolve()
        if protocol_schema_path is not None
        else default_protocol_schema_path().resolve()
    )
    receipt_schema = (
        Path(receipt_schema_path).resolve()
        if receipt_schema_path is not None
        else default_receipt_schema_path().resolve()
    )

    candidates = load_records(input_file)
    candidate_validator = load_validator(protocol_schema)
    valid_candidates, _, input_issues = validate_records(
        candidates,
        candidate_validator,
    )
    if input_issues:
        raise SimulationInputValidationError(_convert_issues(input_issues))

    start = recorded_at or _utc_now()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    start = start.astimezone(timezone.utc)

    resolved_run_id = run_id or _run_id(start)
    if RUN_ID_PATTERN.fullmatch(resolved_run_id) is None:
        raise ValueError(
            "run_id must match ^run-[A-Za-z0-9][A-Za-z0-9._-]*$"
        )

    cases: list[ScenarioCase] = []
    receipts: list[dict[str, Any]] = []
    offset = 0

    for candidate in valid_candidates:
        candidate_cases = generate_suite(candidate, count=scenario_count)
        cases.extend(candidate_cases)

        for case in candidate_cases:
            moment = start + timedelta(milliseconds=offset * 2)
            receipts.append(
                _build_receipt(
                    candidate,
                    case,
                    resolved_run_id,
                    moment,
                )
            )
            offset += 1

    receipt_validator = load_validator(receipt_schema)
    valid_receipts, _, output_issues = validate_records(
        receipts,
        receipt_validator,
    )
    if output_issues:
        raise SimulationOutputValidationError(_convert_issues(output_issues))

    return SimulationResult(
        input_path=input_file,
        protocol_schema_path=protocol_schema,
        receipt_schema_path=receipt_schema,
        run_id=resolved_run_id,
        candidates=valid_candidates,
        cases=cases,
        receipts=valid_receipts,
    )
