"""Simulation-receipt selection for LoPAS Protocol Foundry."""

from .aggregator import AGGREGATOR_VERSION, aggregate_receipts
from .pipeline import SelectionResult, run_selection
from .selector import SELECTOR_VERSION, classify_candidates

__all__ = [
    "AGGREGATOR_VERSION",
    "SELECTOR_VERSION",
    "SelectionResult",
    "aggregate_receipts",
    "classify_candidates",
    "run_selection",
]
