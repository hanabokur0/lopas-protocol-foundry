"""Deterministic Protocol Candidate simulation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .expressions import Evaluation, evaluate_expression
from .scenarios import ScenarioCase


SIMULATOR_VERSION = "deterministic-simulator-0.1.0"

ROUTE_PRIORITY = {
    "AUTO": 1,
    "REVIEW": 2,
    "HOLD": 3,
    "ESCALATE": 4,
    "DENY": 5,
}


@dataclass(frozen=True)
class RouteDecision:
    route: str
    source: str
    reason: str
    blocking: bool


@dataclass(frozen=True)
class EngineResult:
    actual_route: str
    route_reason: str
    task_completed: bool
    factual_error: bool
    policy_violation: bool
    receipt_complete: bool
    supported: bool
    decisions: list[RouteDecision]
    unsupported_expressions: list[str]


def _choose_route(
    default_route: str,
    decisions: list[RouteDecision],
) -> tuple[str, str]:
    if not decisions:
        return default_route, "No override matched; candidate default route used."

    selected = max(
        decisions,
        key=lambda decision: ROUTE_PRIORITY[decision.route],
    )
    return selected.route, selected.reason


def _evaluate_conditions(
    conditions: list[dict[str, Any]],
    variables: dict[str, Any],
    *,
    section: str,
    false_route: str,
) -> tuple[list[RouteDecision], list[str]]:
    decisions: list[RouteDecision] = []
    unsupported: list[str] = []

    for condition in conditions:
        evaluation = evaluate_expression(condition["expression"], variables)

        if not evaluation.supported:
            unsupported.append(condition["expression"])
            decisions.append(
                RouteDecision(
                    route="HOLD",
                    source=section,
                    reason=evaluation.reason,
                    blocking=True,
                )
            )
            continue

        if evaluation.value is None:
            decisions.append(
                RouteDecision(
                    route=condition["on_unknown"],
                    source=section,
                    reason=(
                        f"{condition['description']} "
                        f"{evaluation.reason}"
                    ),
                    blocking=True,
                )
            )
        elif evaluation.value is False:
            decisions.append(
                RouteDecision(
                    route=false_route,
                    source=section,
                    reason=f"Condition false: {condition['description']}",
                    blocking=True,
                )
            )

    return decisions, unsupported


def simulate_case(
    candidate: dict[str, Any],
    case: ScenarioCase,
) -> EngineResult:
    """Evaluate one candidate in one scenario without executing external tools."""
    variables = case.scenario["variables"]
    decisions: list[RouteDecision] = []
    unsupported: list[str] = []

    requested_action = variables.get("requested_action")
    forbidden_actions = candidate["safety"].get("forbidden_actions", [])
    if requested_action in forbidden_actions:
        decisions.append(
            RouteDecision(
                route="DENY",
                source="safety",
                reason=f"Requested action {requested_action!r} is forbidden.",
                blocking=True,
            )
        )

    missing_input = variables.get("missing_required_input")
    if isinstance(missing_input, str) and missing_input:
        decisions.append(
            RouteDecision(
                route="HOLD",
                source="inputs",
                reason=f"Required input {missing_input!r} is unavailable.",
                blocking=True,
            )
        )

    trigger_decisions, trigger_unsupported = _evaluate_conditions(
        candidate["trigger"]["conditions"],
        variables,
        section="trigger",
        false_route="HOLD",
    )
    decisions.extend(trigger_decisions)
    unsupported.extend(trigger_unsupported)

    precondition_decisions, precondition_unsupported = _evaluate_conditions(
        candidate["preconditions"],
        variables,
        section="precondition",
        false_route="HOLD",
    )
    decisions.extend(precondition_decisions)
    unsupported.extend(precondition_unsupported)

    for rule in candidate["routing"]["rules"]:
        evaluation = evaluate_expression(
            rule["when"]["expression"],
            variables,
        )

        if not evaluation.supported:
            unsupported.append(rule["when"]["expression"])
            decisions.append(
                RouteDecision(
                    route="HOLD",
                    source="routing_rule",
                    reason=evaluation.reason,
                    blocking=True,
                )
            )
        elif evaluation.value is None:
            decisions.append(
                RouteDecision(
                    route=rule["when"]["on_unknown"],
                    source="routing_rule",
                    reason=(
                        f"{rule['when']['description']} "
                        f"{evaluation.reason}"
                    ),
                    blocking=True,
                )
            )
        elif evaluation.value is True:
            decisions.append(
                RouteDecision(
                    route=rule["route"],
                    source="routing_rule",
                    reason=rule["reason"],
                    blocking=rule["route"] != "AUTO",
                )
            )

    for condition in candidate["stop_conditions"]:
        evaluation = evaluate_expression(
            condition["expression"],
            variables,
        )

        if not evaluation.supported:
            unsupported.append(condition["expression"])
            decisions.append(
                RouteDecision(
                    route="HOLD",
                    source="stop_condition",
                    reason=evaluation.reason,
                    blocking=True,
                )
            )
        elif evaluation.value is None:
            decisions.append(
                RouteDecision(
                    route=condition["on_unknown"],
                    source="stop_condition",
                    reason=(
                        f"{condition['description']} "
                        f"{evaluation.reason}"
                    ),
                    blocking=True,
                )
            )
        elif evaluation.value is True:
            decisions.append(
                RouteDecision(
                    route=candidate["failure_handling"]["default_route"],
                    source="stop_condition",
                    reason=f"Stop condition true: {condition['description']}",
                    blocking=True,
                )
            )

    failure_code = variables.get("forced_failure_code")
    if isinstance(failure_code, str) and failure_code:
        known = {
            failure["code"]: failure
            for failure in candidate["failure_handling"].get(
                "known_failures",
                [],
            )
        }
        if failure_code in known:
            failure = known[failure_code]
            decisions.append(
                RouteDecision(
                    route=failure["route"],
                    source="known_failure",
                    reason=f"Known failure injected: {failure_code}.",
                    blocking=True,
                )
            )
        else:
            decisions.append(
                RouteDecision(
                    route=candidate["failure_handling"]["default_route"],
                    source="unknown_failure",
                    reason=f"Unknown failure injected: {failure_code}.",
                    blocking=True,
                )
            )

    if candidate["safety"]["required_human_review"]:
        approved = variables.get("human_review_approved")
        rejected = variables.get("human_review_rejected")

        if rejected is True or approved is False:
            decisions.append(
                RouteDecision(
                    route=candidate["failure_handling"]["default_route"],
                    source="human_review",
                    reason="Required human review rejected the result.",
                    blocking=True,
                )
            )
        elif approved is None:
            decisions.append(
                RouteDecision(
                    route="REVIEW",
                    source="human_review",
                    reason="Required human review has not been completed.",
                    blocking=True,
                )
            )

    actual_route, route_reason = _choose_route(
        candidate["routing"]["default"],
        decisions,
    )

    factual_error = variables.get("force_factual_error") is True
    policy_violation = (
        requested_action in forbidden_actions and actual_route != "DENY"
    )

    blocking = any(decision.blocking for decision in decisions)
    task_completed = (
        actual_route in {"AUTO", "REVIEW"}
        and not blocking
        and not factual_error
        and not policy_violation
    )

    return EngineResult(
        actual_route=actual_route,
        route_reason=route_reason,
        task_completed=task_completed,
        factual_error=factual_error,
        policy_violation=policy_violation,
        receipt_complete=True,
        supported=not unsupported,
        decisions=decisions,
        unsupported_expressions=sorted(set(unsupported)),
    )
