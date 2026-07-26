"""Command-line interface for Proxy generation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.ingest.errors import IngestError
from src.ingest.pipeline import write_yaml

from .errors import (
    ProxyError,
    ProxyInputValidationError,
    ProxyOutputValidationError,
)
from .pipeline import (
    build_proxies,
    default_observation_schema_path,
    default_proxy_schema_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.proxy",
        description=(
            "Refine validated Observation documents into conservative Proxy "
            "documents using deterministic baseline rules."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Observation JSONL, JSON, or YAML file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("receipts/sample_run/proxies.yaml"),
        help="Generated Proxy YAML path.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help=(
            "Proxy-generation receipt path. Defaults to the output filename "
            "with '.receipt.yaml' appended."
        ),
    )
    parser.add_argument(
        "--observation-schema",
        type=Path,
        default=default_observation_schema_path(),
    )
    parser.add_argument(
        "--proxy-schema",
        type=Path,
        default=default_proxy_schema_path(),
    )
    return parser


def _error_receipt(
    input_path: Path,
    error: ProxyInputValidationError | ProxyOutputValidationError,
) -> dict:
    stage = (
        "input_validation"
        if isinstance(error, ProxyInputValidationError)
        else "output_validation"
    )
    return {
        "schema_version": "0.1.0",
        "receipt_type": "proxy_generation",
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
        result = build_proxies(
            args.input,
            observation_schema_path=args.observation_schema,
            proxy_schema_path=args.proxy_schema,
        )
    except (ProxyInputValidationError, ProxyOutputValidationError) as exc:
        write_yaml(receipt_path, _error_receipt(args.input, exc))
        print(f"proxy generation failed: {exc}", file=sys.stderr)
        for issue in exc.issues:
            identity = issue.record_id or f"record[{issue.record_index}]"
            print(
                f"- {identity} {issue.path}: {issue.message}",
                file=sys.stderr,
            )
        print(f"receipt: {receipt_path}")
        return 2
    except (ProxyError, IngestError, OSError, ValueError) as exc:
        print(f"proxy error: {exc}", file=sys.stderr)
        return 1

    write_yaml(args.output, result.proxies)
    write_yaml(receipt_path, result.receipt())

    print(
        "proxy:"
        f" observations={len(result.observations)}"
        f" proxies={len(result.proxies)}"
    )
    print(f"output: {args.output}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
