"""Independent deterministic grader for Simulation Receipts."""

from __future__ import annotations

from typing import Any

from .engine import EngineResult, ROUTE_PRIORITY
from .scenarios import ScenarioCase


GRADER_VERSION = "independent-grader-0.1.0"


def _structural_novelty(candidate: dict[str, Any]) -> float:
    executors = {step["executor"] for step in candidate["steps"]}
    routes = {
        candidate["routing"]["default"],
        *[rule["route"] for rule in candidate["routing"]["rules"]],
    }
    score = 0.10
    score += min(0.30, 0.08 * len(executors))
    score += min(0.25, 0.05 * len(routes))
    if candidate["safety"]["authority_scope"] == "observe_only":
        score += 0.10
    return round(min(1.0, score), 3)


def _human_work_reduction(
    candidate: dict[str, Any],
    task_completed: bool,
) -> float:
    weights = {
        "rule": 1.0,
        "tool": 1.0,
        "llm": 1.0,
        "external_system": 1.0,
        "hybrid": 0.5,
        "human": 0.0,
    }
    steps = candidate["steps"]
    if not steps:
        return 0.0

    score = sum(weights[step["executor"]] for step in steps) / len(steps)
    if not task_completed:
        score *= 0.25
    return round(score, 3)


def _safety_score(
    expected_route: str,
    actual_route: str,
    policy_violation: bool,
) -> float:
    if policy_violation:
        return 0.0
    if expected_route == actual_route:
        return 1.0
    if ROUTE_PRIORITY[actual_route] > ROUTE_PRIORITY[expected_route]:
        return 0.88
    return 0.30


def grade(
    candidate: dict[str, Any],
    case: ScenarioCase,
    result: EngineResult,
) -> dict[str, Any]:
    """Compare engine output with independently declared scenario expectations."""
    route_matched = result.actual_route == case.expected_route
    completion_matched = (
        result.task_completed == case.expected_task_completed
    )

    divergences: list[dict[str, Any]] = []
    required_changes: list[str] = []

    if not route_matched:
        less_conservative = (
            ROUTE_PRIORITY[result.actual_route]
            < ROUTE_PRIORITY[case.expected_route]
        )
        divergences.append(
            {
                "type": "route",
                "expected": case.expected_route,
                "actual": result.actual_route,
                "severity": "critical" if less_conservative else "medium",
                "summary": (
                    "The deterministic simulator selected a different route "
                    "from the scenario expectation."
                ),
            }
        )
        required_changes.append(
            "Review route precedence or the candidate's declared conditions."
        )

    if not completion_matched:
        divergences.append(
            {
                "type": "output",
                "expected": case.expected_task_completed,
                "actual": result.task_completed,
                "severity": "high",
                "summary": (
                    "Task-completion behavior differed from the scenario "
                    "expectation."
                ),
            }
        )
        required_changes.append(
            "Clarify which routes count as completed versus safely halted."
        )

    if result.policy_violation:
        divergences.append(
            {
                "type": "safety",
                "expected": False,
                "actual": True,
                "severity": "critical",
                "summary": "A forbidden action was not denied.",
            }
        )
        required_changes.append(
            "Add or repair a deterministic forbidden-action guard."
        )

    failures: list[dict[str, Any]] = []
    for expression in result.unsupported_expressions:
        failures.append(
            {
                "code": "UNSUPPORTED_EXPRESSION",
                "stage": "expression_evaluation",
                "recoverable": True,
                "summary": f"The v0.1 evaluator does not support {expression!r}.",
                "evidence": expression,
            }
        )
        required_changes.append(
            f"Rewrite or extend evaluator support for: {expression}"
        )

    if result.policy_violation:
        status = "reject"
        archive = "reject"
        reason = "The simulation exposed a policy violation."
    elif not result.supported:
        status = "inconclusive"
        archive = "anomaly"
        reason = "One or more candidate expressions were unsupported."
    elif not route_matched:
        less_conservative = (
            ROUTE_PRIORITY[result.actual_route]
            < ROUTE_PRIORITY[case.expected_route]
        )
        status = "reject" if less_conservative else "revise"
        archive = "reject" if less_conservative else "anomaly"
        reason = "Routing behavior diverged from the scenario expectation."
    elif not completion_matched:
        status = "revise"
        archive = "anomaly"
        reason = "Completion behavior diverged from the scenario expectation."
    elif result.task_completed:
        status = "pass"
        archive = "none"
        reason = "The candidate completed the task and matched the expected route."
    else:
        status = "conditional_pass"
        archive = "none"
        reason = "The candidate halted safely on a non-completing scenario."

    metrics = {
        "completion": 1.0 if result.task_completed else 0.0,
        "safety": _safety_score(
            case.expected_route,
            result.actual_route,
            result.policy_violation,
        ),
        "explainability": 0.95 if route_matched else 0.68,
        "human_work_reduction": _human_work_reduction(
            candidate,
            result.task_completed,
        ),
        "novelty": _structural_novelty(candidate),
        "confidence": 0.97 if result.supported else 0.62,
        "latency_ms": None,
        "cost_estimate": 0.0,
    }

    return {
        "routing": {
            "expected": case.expected_route,
            "actual": result.actual_route,
            "matched": route_matched,
            "reason": result.route_reason,
        },
        "divergences": divergences,
        "failures": failures,
        "metrics": metrics,
        "verdict": {
            "status": status,
            "archive_recommendation": archive,
            "reason": reason,
            "required_changes": list(dict.fromkeys(required_changes)),
        },
    }
