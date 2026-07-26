"""Command-line interface for candidate selection."""

from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

from src.ingest.errors import IngestError
from src.ingest.pipeline import write_yaml

from .errors import (
    MixedSimulationRunsError,
    SelectionError,
    SelectionInputValidationError,
)
from .pipeline import default_receipt_schema_path, run_selection
from .scoring import SelectionThresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.selection",
        description=(
            "Aggregate Simulation Receipts and classify Protocol Candidates "
            "into elite, rare, anomaly, reject, or none."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Simulation Receipt JSONL, JSON, or YAML file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("receipts/sample_run/selection_results.yaml"),
        help="Selection Result YAML path.",
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
    parser.add_argument("--selection-id", default=None)
    parser.add_argument(
        "--recorded-at",
        default=None,
        help="Optional ISO-8601 time for reproducible output.",
    )
    parser.add_argument(
        "--allow-mixed-runs",
        action="store_true",
        help="Allow receipts from more than one simulation run.",
    )
    parser.add_argument(
        "--minimum-receipts",
        type=int,
        default=12,
    )
    parser.add_argument(
        "--minimum-scenario-families",
        type=int,
        default=6,
    )
    parser.add_argument(
        "--elite-minimum-score",
        type=float,
        default=0.84,
    )
    parser.add_argument(
        "--rare-minimum-distance",
        type=float,
        default=0.18,
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt_path = args.receipt or args.output.with_suffix(
        args.output.suffix + ".receipt.yaml"
    )

    thresholds = SelectionThresholds(
        minimum_receipts=args.minimum_receipts,
        minimum_scenario_families=args.minimum_scenario_families,
        elite_minimum_score=args.elite_minimum_score,
        rare_minimum_distance=args.rare_minimum_distance,
    )

    try:
        result = run_selection(
            args.input,
            thresholds=thresholds,
            selection_id=args.selection_id,
            recorded_at=_parse_recorded_at(args.recorded_at),
            allow_mixed_runs=args.allow_mixed_runs,
            receipt_schema_path=args.receipt_schema,
        )
    except SelectionInputValidationError as exc:
        print(f"selection failed: {exc}", file=sys.stderr)
        for issue in exc.issues:
            identity = issue.record_id or f"record[{issue.record_index}]"
            print(
                f"- {identity} {issue.path}: {issue.message}",
                file=sys.stderr,
            )
        return 2
    except MixedSimulationRunsError as exc:
        print(f"selection failed: {exc}", file=sys.stderr)
        print(
            "Use --allow-mixed-runs only when cross-run comparison is intentional.",
            file=sys.stderr,
        )
        return 2
    except (SelectionError, IngestError, OSError, ValueError) as exc:
        print(f"selection error: {exc}", file=sys.stderr)
        return 1

    write_yaml(args.output, result.document)
    write_yaml(receipt_path, result.stage_receipt())

    summary = result.document["summary"]
    print(
        "selection:"
        f" receipts={len(result.receipts)}"
        f" candidates={summary['candidate_count']}"
    )
    print(
        "archives:"
        + " ".join(
            f"{archive}={count}"
            for archive, count
            in summary["membership_counts"].items()
        )
    )
    print(f"output: {args.output}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
