"""Command-line interface for deterministic candidate simulation."""

from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

from src.ingest.errors import IngestError
from src.ingest.pipeline import write_yaml

from .errors import (
    SimulationError,
    SimulationInputValidationError,
    SimulationOutputValidationError,
)
from .pipeline import (
    default_protocol_schema_path,
    default_receipt_schema_path,
    run_simulation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.simulation",
        description=(
            "Generate deterministic synthetic scenarios, simulate Protocol "
            "Candidates, and emit schema-valid Simulation Receipts."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Protocol Candidate JSONL, JSON, or YAML file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("receipts/sample_run/simulation_receipts.yaml"),
        help="Generated Simulation Receipt YAML path.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help=(
            "Stage receipt path. Defaults to the output filename with "
            "'.receipt.yaml' appended."
        ),
    )
    parser.add_argument(
        "--scenario-count",
        type=int,
        default=None,
        help=(
            "Scenarios per candidate. When omitted, each candidate's "
            "activation.required_simulations value is used."
        ),
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional stable run identifier beginning with 'run-'.",
    )
    parser.add_argument(
        "--recorded-at",
        default=None,
        help=(
            "Optional ISO-8601 run time for reproducible output, for example "
            "2026-07-26T06:30:00+00:00."
        ),
    )
    parser.add_argument(
        "--protocol-schema",
        type=Path,
        default=default_protocol_schema_path(),
    )
    parser.add_argument(
        "--receipt-schema",
        type=Path,
        default=default_receipt_schema_path(),
    )
    return parser


def _parse_recorded_at(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid --recorded-at value: {raw}") from exc


def _error_receipt(
    input_path: Path,
    error: SimulationInputValidationError | SimulationOutputValidationError,
) -> dict:
    stage = (
        "input_validation"
        if isinstance(error, SimulationInputValidationError)
        else "output_validation"
    )
    return {
        "schema_version": "0.1.0",
        "receipt_type": "simulation_run",
        "input": {"path": str(input_path)},
        "status": "failed",
        "failed_stage": stage,
        "issues": [issue.as_dict() for issue in error.issues],
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt_path = args.receipt or args.output.with_suffix(
        args.output.suffix + ".receipt.yaml"
    )

    try:
        recorded_at = _parse_recorded_at(args.recorded_at)
        result = run_simulation(
            args.input,
            scenario_count=args.scenario_count,
            run_id=args.run_id,
            recorded_at=recorded_at,
            protocol_schema_path=args.protocol_schema,
            receipt_schema_path=args.receipt_schema,
        )
    except (
        SimulationInputValidationError,
        SimulationOutputValidationError,
    ) as exc:
        write_yaml(receipt_path, _error_receipt(args.input, exc))
        print(f"simulation failed: {exc}", file=sys.stderr)
        for issue in exc.issues:
            identity = issue.record_id or f"record[{issue.record_index}]"
            print(
                f"- {identity} {issue.path}: {issue.message}",
                file=sys.stderr,
            )
        print(f"receipt: {receipt_path}")
        return 2
    except (SimulationError, IngestError, OSError, ValueError) as exc:
        print(f"simulation error: {exc}", file=sys.stderr)
        return 1

    write_yaml(args.output, result.receipts)
    write_yaml(receipt_path, result.stage_receipt())

    print(
        "simulation:"
        f" candidates={len(result.candidates)}"
        f" scenarios={len(result.cases)}"
        f" receipts={len(result.receipts)}"
    )
    print(f"run_id: {result.run_id}")
    print(f"output: {args.output}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
