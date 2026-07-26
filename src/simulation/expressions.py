"""Small, explicit expression evaluator used by the deterministic simulator.

The v0.1 evaluator intentionally supports only one-variable comparisons:

    variable == true
    variable != 'value'
    variable <= 60
    variable > 0

Unsupported expressions are reported as unknown rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


EXPRESSION_EVALUATOR_VERSION = "expression-evaluator-0.1.0"

_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?P<operator>==|!=|<=|>=|<|>)\s*"
    r"(?P<literal>.+?)\s*$"
)


@dataclass(frozen=True)
class ParsedExpression:
    name: str
    operator: str
    literal: Any


@dataclass(frozen=True)
class Evaluation:
    value: bool | None
    supported: bool
    variable: str | None
    reason: str


def _parse_literal(raw: str) -> tuple[Any, bool]:
    value = raw.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1], True

    lowered = value.lower()
    if lowered == "true":
        return True, True
    if lowered == "false":
        return False, True
    if lowered in {"null", "none"}:
        return None, True

    try:
        if any(character in value for character in ".eE"):
            return float(value), True
        return int(value), True
    except ValueError:
        return None, False


def parse_expression(expression: str) -> ParsedExpression | None:
    """Parse a supported one-variable comparison."""
    match = _PATTERN.match(expression)
    if match is None:
        return None

    literal, valid = _parse_literal(match.group("literal"))
    if not valid:
        return None

    return ParsedExpression(
        name=match.group("name"),
        operator=match.group("operator"),
        literal=literal,
    )


def evaluate_expression(
    expression: str,
    variables: dict[str, Any],
) -> Evaluation:
    """Evaluate a supported expression against primitive scenario variables."""
    parsed = parse_expression(expression)
    if parsed is None:
        return Evaluation(
            value=None,
            supported=False,
            variable=None,
            reason=f"Unsupported expression: {expression}",
        )

    if parsed.name not in variables:
        return Evaluation(
            value=None,
            supported=True,
            variable=parsed.name,
            reason=f"Variable {parsed.name!r} is unknown.",
        )

    left = variables[parsed.name]
    right = parsed.literal

    try:
        if parsed.operator == "==":
            result = left == right
        elif parsed.operator == "!=":
            result = left != right
        elif parsed.operator == "<=":
            result = left <= right
        elif parsed.operator == ">=":
            result = left >= right
        elif parsed.operator == "<":
            result = left < right
        elif parsed.operator == ">":
            result = left > right
        else:  # pragma: no cover - parser constrains operators
            raise AssertionError(parsed.operator)
    except TypeError:
        return Evaluation(
            value=None,
            supported=True,
            variable=parsed.name,
            reason=(
                f"Variable {parsed.name!r} cannot be compared with "
                f"{right!r} using {parsed.operator}."
            ),
        )

    return Evaluation(
        value=bool(result),
        supported=True,
        variable=parsed.name,
        reason=f"{expression} evaluated to {bool(result)}.",
    )


def value_for_expression(expression: str, desired: bool) -> tuple[str, Any] | None:
    """Return one simple variable assignment that makes an expression true/false."""
    parsed = parse_expression(expression)
    if parsed is None:
        return None

    right = parsed.literal
    operator = parsed.operator

    if operator == "==":
        value = right if desired else _different_value(right)
    elif operator == "!=":
        value = _different_value(right) if desired else right
    elif not isinstance(right, (int, float)) or isinstance(right, bool):
        return None
    elif operator == "<=":
        value = right if desired else right + 1
    elif operator == ">=":
        value = right if desired else right - 1
    elif operator == "<":
        value = right - 1 if desired else right
    elif operator == ">":
        value = right + 1 if desired else right
    else:  # pragma: no cover
        return None

    return parsed.name, value


def _different_value(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if value is None:
        return "known"
    if isinstance(value, str):
        return f"not-{value}"
    if isinstance(value, (int, float)):
        return value + 1
    return "different"
