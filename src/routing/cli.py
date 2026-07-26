"""Command-line interface for PoC promotion routing."""

from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

from src.ingest.errors import IngestError
from src.ingest.pipeline import write_yaml

from .errors import (
    RoutingCandidateValidationError,
    RoutingError,
    RoutingPromotionValidationError,
)
from .pipeline import (
    default_candidate_schema_path,
    default_promotion_schema_path,
    run_routing,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.routing",
        description=(
            "Match Protocol Candidates with Selection Results and produce "
            "schema-valid PoC Promotion decisions."
        ),
    )
    parser.add_argument(
        "candidates",
        type=Path,
        help="Protocol Candidate YAML/JSON file.",
    )
    parser.add_argument(
        "selection",
        type=Path,
        help="Selection Result YAML/JSON file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("receipts/sample_run/poc_promotions.yaml"),
        help="PoC Promotion YAML path.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help=(
            "Routing-stage receipt path. Defaults to the output filename with "
            "'.receipt.yaml' appended."
        ),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=None,
        help=(
            "Optional evidence manifest containing source diversity, monitoring, "
            "rollback, and human approval evidence."
        ),
    )
    parser.add_argument("--current-level", type=int, default=1)
    parser.add_argument("--next-level", type=int, default=2)
    parser.add_argument(
        "--decided-at",
        default=None,
        help="Optional ISO-8601 time for reproducible output.",
    )
    parser.add_argument(
        "--recorded-by",
        default="lopas-protocol-foundry",
    )
    parser.add_argument(
        "--candidate-schema",
        type=Path,
        default=default_candidate_schema_path(),
    )
    parser.add_argument(
        "--promotion-schema",
        type=Path,
        default=default_promotion_schema_path(),
    )
    return parser


def _parse_datetime(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid --decided-at value: {raw}") from exc


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt_path = args.receipt or args.output.with_suffix(
        args.output.suffix + ".receipt.yaml"
    )

    try:
        result = run_routing(
            args.candidates,
            args.selection,
            evidence_path=args.evidence,
            current_level=args.current_level,
            requested_next_level=args.next_level,
            decided_at=_parse_datetime(args.decided_at),
            recorded_by=args.recorded_by,
            candidate_schema_path=args.candidate_schema,
            promotion_schema_path=args.promotion_schema,
        )
    except (
        RoutingCandidateValidationError,
        RoutingPromotionValidationError,
    ) as exc:
        print(f"routing failed: {exc}", file=sys.stderr)
        for issue in exc.issues:
            identity = issue.record_id or f"record[{issue.record_index}]"
            print(
                f"- {identity} {issue.path}: {issue.message}",
                file=sys.stderr,
            )
        return 2
    except (RoutingError, IngestError, OSError, ValueError) as exc:
        print(f"routing error: {exc}", file=sys.stderr)
        return 1

    write_yaml(args.output, result.promotions)
    write_yaml(receipt_path, result.stage_receipt())

    route_counts: dict[str, int] = {}
    for promotion in result.promotions:
        route = promotion["decision"]["route"]
        route_counts[route] = route_counts.get(route, 0) + 1

    print(
        "routing:"
        f" candidates={len(result.candidates)}"
        f" promotions={len(result.promotions)}"
    )
    print(
        "routes:"
        + " ".join(
            f"{route}={count}"
            for route, count in sorted(route_counts.items())
        )
    )
    print(f"output: {args.output}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
