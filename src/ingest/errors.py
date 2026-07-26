"""Typed errors raised by the ingest stage."""

from __future__ import annotations


class IngestError(Exception):
    """Base class for ingest failures."""


class UnsupportedFormatError(IngestError):
    """Raised when an input file format is unsupported."""


class InputParseError(IngestError):
    """Raised when JSON or YAML input cannot be parsed."""


class SchemaLoadError(IngestError):
    """Raised when the observation schema cannot be loaded."""
