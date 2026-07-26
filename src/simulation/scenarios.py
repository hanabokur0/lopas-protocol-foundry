"""Generate deterministic scenario suites from Protocol Candidates."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import re
from typing import Any

from .expressions import value_for_expression


SCENARIO_GENERATOR_VERSION = "scenario-generator-0.1.0"


@dataclass(frozen=True)
class ScenarioCase:
    """Internal scenario plus the expected result used by the grader."""

    scenario: dict[str, Any]
    expected_route: str
    expected_task_completed: bool
    archetype: str


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower() or "case"


def _base_variables(candidate: dict[str, Any]) -> dict[str, Any]:
    """Build a nominal environment where declared conditions are known."""
    variables: dict[str, Any] = {
        "human_review_approved": True,
        "human_review_rejected": False,
        "missing_required_input": None,
        "requested_action": None,
        "forced_failure_code": None,
        "force_factual_error": False,
    }

    for section in (
        candidate["trigger"]["conditions"],
        candidate["preconditions"],
    ):
        for condition in section:
            assignment = value_for_expression(condition["expression"], True)
            if assignment is not None:
                variables[assignment[0]] = assignment[1]

    for rule in candidate["routing"]["rules"]:
        assignment = value_for_expression(rule["when"]["expression"], False)
        if assignment is not None:
            variables[assignment[0]] = assignment[1]

    for condition in candidate["stop_conditions"]:
        assignment = value_for_expression(condition["expression"], False)
        if assignment is not None:
            variables[assignment[0]] = assignment[1]

    return variables


def _scenario(
    candidate: dict[str, Any],
    suffix: str,
    summary: str,
    variables: dict[str, Any],
    expected_route: str,
    expected_task_completed: bool,
    *,
    adversarial: bool = False,
    archetype: str,
) -> ScenarioCase:
    candidate_suffix = candidate["id"].removeprefix("protocol-")
    return ScenarioCase(
        scenario={
            "id": f"scenario-{candidate_suffix}-{suffix}",
            "type": "synthetic",
            "summary": summary,
            "adversarial": adversarial,
            "variables": variables,
            "source_refs": list(
                candidate["provenance"].get("observation_refs", [])
            ),
        },
        expected_route=expected_route,
        expected_task_completed=expected_task_completed,
        archetype=archetype,
    )


def _core_suite(candidate: dict[str, Any]) -> list[ScenarioCase]:
    base = _base_variables(candidate)
    cases: list[ScenarioCase] = []

    cases.append(
        _scenario(
            candidate,
            "nominal",
            "All declared trigger and precondition values are available.",
            deepcopy(base),
            candidate["routing"]["default"],
            True,
            archetype="nominal",
        )
    )

    if candidate["inputs"]["required"]:
        variables = deepcopy(base)
        missing_input = candidate["inputs"]["required"][0]
        variables["missing_required_input"] = missing_input
        cases.append(
            _scenario(
                candidate,
                "missing-required-input",
                f"Required input {missing_input!r} is unavailable.",
                variables,
                "HOLD",
                False,
                archetype="missing_required_input",
            )
        )

    condition_pool = [
        *candidate["trigger"]["conditions"],
        *candidate["preconditions"],
    ]
    if condition_pool:
        condition = condition_pool[0]
        assignment = value_for_expression(condition["expression"], True)
        if assignment is not None:
            variables = deepcopy(base)
            variables.pop(assignment[0], None)
            cases.append(
                _scenario(
                    candidate,
                    "unknown-condition",
                    (
                        f"Variable {assignment[0]!r} is absent while evaluating "
                        f"{condition['expression']!r}."
                    ),
                    variables,
                    condition["on_unknown"],
                    False,
                    archetype="unknown_condition",
                )
            )

            false_assignment = value_for_expression(
                condition["expression"],
                False,
            )
            if false_assignment is not None:
                variables = deepcopy(base)
                variables[false_assignment[0]] = false_assignment[1]
                cases.append(
                    _scenario(
                        candidate,
                        "false-condition",
                        f"Declared condition {condition['expression']!r} is false.",
                        variables,
                        "HOLD",
                        False,
                        archetype="false_condition",
                    )
                )

    if candidate["safety"]["required_human_review"]:
        variables = deepcopy(base)
        variables["human_review_approved"] = False
        variables["human_review_rejected"] = True
        cases.append(
            _scenario(
                candidate,
                "human-review-rejected",
                "The required human reviewer rejects the generated draft.",
                variables,
                candidate["failure_handling"]["default_route"],
                False,
                archetype="human_review_rejected",
            )
        )

    for index, rule in enumerate(candidate["routing"]["rules"], start=1):
        assignment = value_for_expression(rule["when"]["expression"], True)
        if assignment is None:
            continue
        variables = deepcopy(base)
        variables[assignment[0]] = assignment[1]
        cases.append(
            _scenario(
                candidate,
                f"routing-rule-{index:02d}",
                f"Routing rule becomes true: {rule['when']['description']}",
                variables,
                rule["route"],
                rule["route"] == "AUTO",
                adversarial=rule["route"] in {"DENY", "ESCALATE"},
                archetype="routing_rule",
            )
        )

    if candidate["stop_conditions"]:
        condition = candidate["stop_conditions"][0]
        assignment = value_for_expression(condition["expression"], True)
        if assignment is not None:
            variables = deepcopy(base)
            variables[assignment[0]] = assignment[1]
            cases.append(
                _scenario(
                    candidate,
                    "stop-condition",
                    f"Stop condition becomes true: {condition['description']}",
                    variables,
                    candidate["failure_handling"]["default_route"],
                    False,
                    archetype="stop_condition",
                )
            )

    known_failures = candidate["failure_handling"].get("known_failures", [])
    if known_failures:
        failure = known_failures[0]
        variables = deepcopy(base)
        variables["forced_failure_code"] = failure["code"]
        cases.append(
            _scenario(
                candidate,
                "known-failure",
                f"Known failure is injected: {failure['code']}.",
                variables,
                failure["route"],
                False,
                archetype="known_failure",
            )
        )

    forbidden_actions = candidate["safety"].get("forbidden_actions", [])
    if forbidden_actions:
        forbidden = forbidden_actions[0]
        variables = deepcopy(base)
        variables["requested_action"] = forbidden
        cases.append(
            _scenario(
                candidate,
                "forbidden-action",
                f"A forbidden action is requested: {forbidden}.",
                variables,
                "DENY",
                False,
                adversarial=True,
                archetype="forbidden_action",
            )
        )

    applicable_rules: list[tuple[dict[str, Any], tuple[str, Any]]] = []
    for rule in candidate["routing"]["rules"]:
        assignment = value_for_expression(rule["when"]["expression"], True)
        if assignment is not None:
            applicable_rules.append((rule, assignment))

    if len(applicable_rules) >= 2:
        variables = deepcopy(base)
        expected_routes: list[str] = []
        for rule, assignment in applicable_rules[:2]:
            variables[assignment[0]] = assignment[1]
            expected_routes.append(rule["route"])

        priority = {
            "AUTO": 1,
            "REVIEW": 2,
            "HOLD": 3,
            "ESCALATE": 4,
            "DENY": 5,
        }
        expected_route = max(expected_routes, key=priority.__getitem__)
        cases.append(
            _scenario(
                candidate,
                "conflicting-routes",
                "Two routing rules are true at the same time.",
                variables,
                expected_route,
                False,
                adversarial=True,
                archetype="conflicting_routes",
            )
        )

    return cases


def _variant(case: ScenarioCase, variant_index: int) -> ScenarioCase:
    """Create a traceable variant without changing the expected behavior."""
    scenario = deepcopy(case.scenario)
    scenario["id"] = f"{scenario['id']}-v{variant_index:02d}"
    scenario["summary"] = (
        f"{scenario['summary']} Deterministic workload variant "
        f"{variant_index:02d}."
    )
    scenario["variables"]["variant_index"] = variant_index
    scenario["variables"]["workload_size"] = 1 + (variant_index % 5)
    return replace(case, scenario=scenario)


def generate_suite(
    candidate: dict[str, Any],
    count: int | None = None,
) -> list[ScenarioCase]:
    """Generate a deterministic scenario suite for one candidate.

    When ``count`` is omitted, the candidate's own
    ``activation.required_simulations`` value is used. Variants preserve
    archetype expectations; later promotion logic must still evaluate scenario
    diversity rather than treating raw count as proof of coverage.
    """
    target = count or candidate["activation"]["required_simulations"]
    if target < 1:
        raise ValueError("Scenario count must be at least 1.")

    core = _core_suite(candidate)
    if not core:
        raise ValueError(f"No scenarios could be generated for {candidate['id']}.")

    if target <= len(core):
        return core[:target]

    suite = list(core)
    variant_index = 1
    while len(suite) < target:
        source = core[(len(suite) - len(core)) % len(core)]
        suite.append(_variant(source, variant_index))
        variant_index += 1

    return suite
