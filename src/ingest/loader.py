"""Load JSONL, JSON, or YAML observation documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from .errors import InputParseError, UnsupportedFormatError


SUPPORTED_SUFFIXES = {".jsonl", ".ndjson", ".json", ".yaml", ".yml"}


def _flatten_documents(documents: Iterable[Any]) -> list[dict[str, Any]]:
    """Flatten YAML/JSON documents into a list of observation objects."""
    records: list[dict[str, Any]] = []

    for document in documents:
        if document is None:
            continue

        if isinstance(document, list):
            for item in document:
                if not isinstance(item, dict):
                    raise InputParseError(
                        "Every observation must be an object; "
                        f"received {type(item).__name__}."
                    )
                records.append(item)
            continue

        if not isinstance(document, dict):
            raise InputParseError(
                "Every observation document must be an object or a list of objects; "
                f"received {type(document).__name__}."
            )

        records.append(document)

    return records


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load one JSON object per non-empty line."""
    records: list[dict[str, Any]] = []

    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise InputParseError(
                        f"{path}:{line_number}: invalid JSON: {exc.msg}"
                    ) from exc

                if not isinstance(value, dict):
                    raise InputParseError(
                        f"{path}:{line_number}: expected an object, "
                        f"received {type(value).__name__}."
                    )

                records.append(value)
    except OSError as exc:
        raise InputParseError(f"Could not read {path}: {exc}") from exc

    return records


def load_json(path: Path) -> list[dict[str, Any]]:
    """Load a JSON object or array of objects."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputParseError(f"Could not read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputParseError(f"{path}: invalid JSON: {exc.msg}") from exc

    return _flatten_documents([value])


def load_yaml(path: Path) -> list[dict[str, Any]]:
    """Load one or more YAML documents."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            documents = list(yaml.safe_load_all(handle))
    except OSError as exc:
        raise InputParseError(f"Could not read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise InputParseError(f"{path}: invalid YAML: {exc}") from exc

    return _flatten_documents(documents)


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Load observations based on the input file suffix."""
    input_path = Path(path)
    suffix = input_path.suffix.lower()

    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise UnsupportedFormatError(
            f"Unsupported input format '{suffix or '<none>'}'. "
            f"Supported formats: {supported}"
        )

    if suffix in {".jsonl", ".ndjson"}:
        return load_jsonl(input_path)
    if suffix == ".json":
        return load_json(input_path)
    return load_yaml(input_path)
