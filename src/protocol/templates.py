"""Deterministic protocol templates for the v0.1 baseline."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PROTOCOL_TEMPLATE_VERSION = "protocol-templates-0.1.0"


TEMPLATES: dict[str, dict[str, Any]] = {
    "meeting_preparation": {
        "description": (
            "Prepare a human-reviewable meeting agenda and note template from "
            "available event context and previous decisions."
        ),
        "trigger": {
            "event": "calendar_event_upcoming",
            "conditions": [
                {
                    "expression": "minutes_until_start <= 60",
                    "description": "The meeting begins within one hour.",
                    "on_unknown": "HOLD",
                },
                {
                    "expression": "meeting_type != 'casual'",
                    "description": "The event requires structured preparation.",
                    "on_unknown": "REVIEW",
                },
            ],
        },
        "inputs": {
            "required": ["calendar_event"],
            "optional": [
                "previous_meeting_receipts",
                "project_context",
                "participant_context",
            ],
        },
        "preconditions": [
            {
                "expression": "calendar_event_available == true",
                "description": "A readable calendar event is available.",
                "on_unknown": "HOLD",
            }
        ],
        "steps": [
            {
                "id": "step-retrieve-decisions",
                "action": "retrieve_previous_decisions",
                "executor": "tool",
                "description": "Retrieve relevant previous decisions and open items.",
                "input_refs": ["previous_meeting_receipts", "project_context"],
                "output_refs": ["previous_decisions", "open_items"],
                "requires_human_confirmation": False,
                "on_failure": "HOLD",
            },
            {
                "id": "step-structure-agenda",
                "action": "generate_draft_agenda",
                "executor": "llm",
                "description": (
                    "Generate a draft agenda grounded in the event and retrieved "
                    "decision records."
                ),
                "input_refs": ["calendar_event", "previous_decisions", "open_items"],
                "output_refs": ["draft_agenda"],
                "requires_human_confirmation": False,
                "on_failure": "REVIEW",
            },
            {
                "id": "step-generate-notes",
                "action": "generate_note_template",
                "executor": "llm",
                "description": (
                    "Generate a note template that separates decisions, actions, "
                    "open questions, and evidence references."
                ),
                "input_refs": ["draft_agenda"],
                "output_refs": ["note_template"],
                "requires_human_confirmation": False,
                "on_failure": "REVIEW",
            },
            {
                "id": "step-review-draft",
                "action": "request_human_review",
                "executor": "human",
                "description": "Review the agenda and note template before use.",
                "input_refs": ["draft_agenda", "note_template"],
                "output_refs": ["review_decision"],
                "requires_human_confirmation": True,
                "on_failure": "ABORT",
            },
        ],
        "routing_rules": [
            {
                "when": {
                    "expression": "confidential_context_detected == true",
                    "description": "Confidential meeting context is present.",
                    "on_unknown": "ESCALATE",
                },
                "route": "ESCALATE",
                "reason": "Confidential context requires an authorized reviewer.",
            },
            {
                "when": {
                    "expression": "conflicting_decisions_detected == true",
                    "description": "Retrieved decisions conflict with one another.",
                    "on_unknown": "HOLD",
                },
                "route": "ESCALATE",
                "reason": "The protocol must not resolve decision conflicts silently.",
            },
            {
                "when": {
                    "expression": "required_context_missing == true",
                    "description": "A required meeting input is unavailable.",
                    "on_unknown": "HOLD",
                },
                "route": "HOLD",
                "reason": "Missing required context prevents grounded preparation.",
            },
        ],
        "stop_conditions": [
            {
                "expression": "human_review_rejected == true",
                "description": "A reviewer rejected the generated draft.",
                "on_unknown": "HOLD",
            }
        ],
        "outputs": [
            {
                "name": "draft_agenda",
                "type": "markdown",
                "description": "A reviewable agenda draft.",
                "sensitive": False,
            },
            {
                "name": "note_template",
                "type": "markdown",
                "description": "A structured meeting-note template.",
                "sensitive": False,
            },
            {
                "name": "review_decision",
                "type": "structured_decision",
                "description": "The human decision to accept, revise, or reject.",
                "sensitive": False,
            },
        ],
        "known_failures": [
            {
                "code": "MISSING_PREVIOUS_CONTEXT",
                "description": "Previous decisions or project context are unavailable.",
                "route": "HOLD",
            },
            {
                "code": "CONFLICTING_DECISIONS",
                "description": "Retrieved decision records conflict.",
                "route": "ESCALATE",
            },
        ],
        "authority_scope": "draft",
        "personal_data_possible": True,
        "forbidden_actions": [
            "send_or_publish_without_review",
            "modify_calendar_event_without_review",
            "invent_missing_decisions",
        ],
    },
    "customer_support": {
        "description": (
            "Inspect a support request for completeness and prepare a "
            "human-reviewable draft response or clarification request."
        ),
        "trigger": {
            "event": "support_request_received",
            "conditions": [
                {
                    "expression": "request_status == 'open'",
                    "description": "The support request is open.",
                    "on_unknown": "HOLD",
                }
            ],
        },
        "inputs": {
            "required": ["support_request"],
            "optional": [
                "attachment_metadata",
                "customer_history",
                "support_policy",
            ],
        },
        "preconditions": [
            {
                "expression": "support_request_readable == true",
                "description": "The request can be read and parsed.",
                "on_unknown": "HOLD",
            }
        ],
        "steps": [
            {
                "id": "step-check-completeness",
                "action": "assess_request_completeness",
                "executor": "rule",
                "description": (
                    "Check required fields and declared attachments before "
                    "drafting a response."
                ),
                "input_refs": ["support_request", "attachment_metadata"],
                "output_refs": ["completeness_assessment"],
                "requires_human_confirmation": False,
                "on_failure": "HOLD",
            },
            {
                "id": "step-draft-response",
                "action": "generate_support_draft",
                "executor": "llm",
                "description": (
                    "Prepare either a clarification request or a grounded response "
                    "draft according to the completeness assessment."
                ),
                "input_refs": [
                    "support_request",
                    "completeness_assessment",
                    "customer_history",
                    "support_policy",
                ],
                "output_refs": ["draft_reply"],
                "requires_human_confirmation": False,
                "on_failure": "REVIEW",
            },
            {
                "id": "step-review-response",
                "action": "request_human_review",
                "executor": "human",
                "description": "Review the support draft before external delivery.",
                "input_refs": ["draft_reply", "completeness_assessment"],
                "output_refs": ["review_decision"],
                "requires_human_confirmation": True,
                "on_failure": "ABORT",
            },
        ],
        "routing_rules": [
            {
                "when": {
                    "expression": "safety_or_legal_claim_detected == true",
                    "description": "The request includes a safety or legal claim.",
                    "on_unknown": "ESCALATE",
                },
                "route": "ESCALATE",
                "reason": "Safety and legal claims require an authorized reviewer.",
            },
            {
                "when": {
                    "expression": "required_information_missing == true",
                    "description": "Required information or an attachment is missing.",
                    "on_unknown": "REVIEW",
                },
                "route": "REVIEW",
                "reason": "A reviewer must approve the clarification request.",
            },
            {
                "when": {
                    "expression": "external_send_requested == true",
                    "description": "The system is asked to send the draft externally.",
                    "on_unknown": "DENY",
                },
                "route": "DENY",
                "reason": "The v0.1 protocol is draft-only and cannot send externally.",
            },
        ],
        "stop_conditions": [
            {
                "expression": "human_review_rejected == true",
                "description": "A reviewer rejected the draft response.",
                "on_unknown": "HOLD",
            }
        ],
        "outputs": [
            {
                "name": "completeness_assessment",
                "type": "structured_assessment",
                "description": "Missing and available request information.",
                "sensitive": True,
            },
            {
                "name": "draft_reply",
                "type": "markdown",
                "description": "A reviewable support-response draft.",
                "sensitive": True,
            },
            {
                "name": "review_decision",
                "type": "structured_decision",
                "description": "The human decision to accept, revise, or reject.",
                "sensitive": False,
            },
        ],
        "known_failures": [
            {
                "code": "UNREADABLE_REQUEST",
                "description": "The support request cannot be parsed reliably.",
                "route": "HOLD",
            },
            {
                "code": "POLICY_CONFLICT",
                "description": "Applicable support policies conflict.",
                "route": "ESCALATE",
            },
        ],
        "authority_scope": "draft",
        "personal_data_possible": True,
        "forbidden_actions": [
            "send_without_review",
            "invent_customer_information",
            "change_account_state",
            "promise_unapproved_compensation",
        ],
    },
}


GENERIC_TEMPLATE: dict[str, Any] = {
    "description": (
        "Prepare an inspectable draft procedure from validated Proxy documents "
        "without performing external actions."
    ),
    "trigger": {
        "event": "manual_protocol_review_requested",
        "conditions": [
            {
                "expression": "authorized_reviewer_available == true",
                "description": "An authorized reviewer is available.",
                "on_unknown": "HOLD",
            }
        ],
    },
    "inputs": {
        "required": ["proxy_context"],
        "optional": ["domain_policy", "historical_receipts"],
    },
    "preconditions": [
        {
            "expression": "proxy_context_validated == true",
            "description": "The source Proxy documents passed schema validation.",
            "on_unknown": "HOLD",
        }
    ],
    "steps": [
        {
            "id": "step-summarize-context",
            "action": "summarize_proxy_context",
            "executor": "rule",
            "description": "Summarize declared friction, effects, constraints, and risks.",
            "input_refs": ["proxy_context"],
            "output_refs": ["structured_context"],
            "requires_human_confirmation": False,
            "on_failure": "HOLD",
        },
        {
            "id": "step-propose-procedure",
            "action": "generate_draft_procedure",
            "executor": "llm",
            "description": (
                "Generate a non-executable draft procedure and mark unresolved "
                "assumptions explicitly."
            ),
            "input_refs": ["structured_context", "domain_policy"],
            "output_refs": ["draft_procedure"],
            "requires_human_confirmation": False,
            "on_failure": "REVIEW",
        },
        {
            "id": "step-review-procedure",
            "action": "request_human_review",
            "executor": "human",
            "description": "Review the draft procedure before simulation.",
            "input_refs": ["draft_procedure"],
            "output_refs": ["review_decision"],
            "requires_human_confirmation": True,
            "on_failure": "ABORT",
        },
    ],
    "routing_rules": [
        {
            "when": {
                "expression": "domain_authority_unknown == true",
                "description": "The authority required by the domain is unknown.",
                "on_unknown": "HOLD",
            },
            "route": "HOLD",
            "reason": "Unknown authority prevents safe protocol promotion.",
        },
        {
            "when": {
                "expression": "high_impact_action_requested == true",
                "description": "A high-impact action is requested.",
                "on_unknown": "DENY",
            },
            "route": "DENY",
            "reason": "The generic baseline is observation and draft only.",
        },
    ],
    "stop_conditions": [
        {
            "expression": "unresolved_assumption_count > 0",
            "description": "One or more material assumptions remain unresolved.",
            "on_unknown": "HOLD",
        }
    ],
    "outputs": [
        {
            "name": "structured_context",
            "type": "yaml",
            "description": "An inspectable summary of source Proxy documents.",
            "sensitive": False,
        },
        {
            "name": "draft_procedure",
            "type": "yaml",
            "description": "A non-executable protocol draft.",
            "sensitive": False,
        },
        {
            "name": "review_decision",
            "type": "structured_decision",
            "description": "The human decision to accept, revise, or reject.",
            "sensitive": False,
        },
    ],
    "known_failures": [
        {
            "code": "UNKNOWN_DOMAIN",
            "description": "No domain-specific protocol template is available.",
            "route": "HOLD",
        }
    ],
    "authority_scope": "observe_only",
    "personal_data_possible": None,
    "forbidden_actions": [
        "perform_external_action",
        "assume_undeclared_authority",
        "hide_unresolved_assumptions",
    ],
}


def get_template(task_type: str) -> tuple[dict[str, Any], bool]:
    """Return a deep-copied template and whether it is task-specific."""
    if task_type in TEMPLATES:
        return deepcopy(TEMPLATES[task_type]), True
    return deepcopy(GENERIC_TEMPLATE), False
