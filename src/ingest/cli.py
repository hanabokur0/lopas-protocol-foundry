"""Command-line interface for observation ingestion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import IngestError
from .pipeline import default_schema_path, ingest_file, write_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.ingest",
        description=(
            "Load JSONL, JSON, or YAML observations and validate them against "
            "schemas/observation.schema.yaml."
        ),
    )
    parser.add_argument("input", type=Path, help="Input JSONL, JSON, or YAML file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("receipts/sample_run/observations.yaml"),
        help="YAML file containing valid observations.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help=(
            "Validation receipt path. Defaults to the output filename with "
            "'.receipt.yaml' appended."
        ),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=default_schema_path(),
        help="Observation JSON Schema YAML path.",
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help=(
            "Write valid records even when some records fail validation. "
            "The command still reports the failures."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt_path = args.receipt or args.output.with_suffix(
        args.output.suffix + ".receipt.yaml"
    )

    try:
        result = ingest_file(args.input, args.schema)
    except IngestError as exc:
        print(f"ingest error: {exc}", file=sys.stderr)
        return 1

    write_yaml(receipt_path, result.receipt())

    if result.is_valid or args.allow_invalid:
        write_yaml(args.output, result.valid_records)

    print(
        "ingest:"
        f" total={result.total_records}"
        f" valid={len(result.valid_records)}"
        f" invalid={len(result.invalid_records)}"
        f" issues={len(result.issues)}"
    )
    print(f"receipt: {receipt_path}")

    if result.is_valid:
        print(f"output: {args.output}")
        return 0

    for issue in result.issues:
        identity = issue.observation_id or f"record[{issue.record_index}]"
        print(
            f"- {identity} {issue.path}: {issue.message}",
            file=sys.stderr,
        )

    if args.allow_invalid:
        print(f"partial output: {args.output}")
    else:
        print("output was not written; use --allow-invalid to keep valid records.")

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
