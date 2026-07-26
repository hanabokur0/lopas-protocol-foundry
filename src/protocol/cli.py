"""Command-line interface for Protocol Candidate generation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.ingest.errors import IngestError
from src.ingest.pipeline import write_yaml

from .errors import (
    ProtocolError,
    ProtocolInputValidationError,
    ProtocolOutputValidationError,
)
from .pipeline import (
    build_protocol_candidates,
    default_protocol_schema_path,
    default_proxy_schema_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.protocol",
        description=(
            "Group validated Proxy documents and generate conservative, "
            "unconfirmed Protocol Candidates."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Proxy JSONL, JSON, or YAML file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("receipts/sample_run/protocol_candidates.yaml"),
        help="Generated Protocol Candidate YAML path.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help=(
            "Generation receipt path. Defaults to the output filename with "
            "'.receipt.yaml' appended."
        ),
    )
    parser.add_argument(
        "--proxy-schema",
        type=Path,
        default=default_proxy_schema_path(),
    )
    parser.add_argument(
        "--protocol-schema",
        type=Path,
        default=default_protocol_schema_path(),
    )
    return parser


def _error_receipt(
    input_path: Path,
    error: ProtocolInputValidationError | ProtocolOutputValidationError,
) -> dict:
    stage = (
        "input_validation"
        if isinstance(error, ProtocolInputValidationError)
        else "output_validation"
    )
    return {
        "schema_version": "0.1.0",
        "receipt_type": "protocol_generation",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
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
        result = build_protocol_candidates(
            args.input,
            proxy_schema_path=args.proxy_schema,
            protocol_schema_path=args.protocol_schema,
        )
    except (
        ProtocolInputValidationError,
        ProtocolOutputValidationError,
    ) as exc:
        write_yaml(receipt_path, _error_receipt(args.input, exc))
        print(f"protocol generation failed: {exc}", file=sys.stderr)
        for issue in exc.issues:
            identity = issue.record_id or f"record[{issue.record_index}]"
            print(
                f"- {identity} {issue.path}: {issue.message}",
                file=sys.stderr,
            )
        print(f"receipt: {receipt_path}")
        return 2
    except (ProtocolError, IngestError, OSError, ValueError) as exc:
        print(f"protocol error: {exc}", file=sys.stderr)
        return 1

    write_yaml(args.output, result.candidates)
    write_yaml(receipt_path, result.receipt())

    print(
        "protocol:"
        f" proxies={len(result.proxies)}"
        f" candidates={len(result.candidates)}"
    )
    print(f"output: {args.output}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
