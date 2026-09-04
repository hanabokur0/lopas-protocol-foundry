#include "lopas/expression.hpp"
#include "lopas/foundry.hpp"

#include <cassert>
#include <iostream>

int main() {
    using namespace lopas;

    {
        Variables vars{{"status", std::string("open")}, {"flag", true}, {"count", 2.0}};
        auto a = evaluate_expression("status == 'open'", vars);
        auto b = evaluate_expression("flag == true", vars);
        auto c = evaluate_expression("count > 0", vars);
        auto d = evaluate_expression("complex && unsupported", vars);
        assert(a.supported && a.value == true);
        assert(b.supported && b.value == true);
        assert(c.supported && c.value == true);
        assert(!d.supported);
    }

    ProtocolCandidate candidate;
    candidate.id = "protocol-test";
    candidate.intent_status = "confirmed";
    candidate.default_route = Route::Auto;
    candidate.failure_default_route = Route::Hold;
    candidate.required_human_review = false;
    candidate.authority_scope = "observe_only";
    candidate.forbidden_actions = {"live_external_write"};
    candidate.trigger_conditions = {{"request_present == true", "request required", Route::Hold}};
    candidate.preconditions = {{"context_ready == true", "context required", Route::Hold}};
    candidate.routing_rules = {{{"risk_high == true", "risk", Route::Hold}, Route::Escalate, "risk escalates"}};
    candidate.stop_conditions = {{"stop_requested == true", "stop", Route::Hold}};
    candidate.known_failures = {{"DEPENDENCY_UNAVAILABLE", Route::Hold}};
    candidate.steps = {{"s1","rule","normalize"}, {"s2","tool","safe_lookup"}};

    {
        ScenarioCase s;
        s.id = "forbidden";
        s.family = "forbidden_action";
        s.variables = {{"request_present", true}, {"context_ready", true}, {"risk_high", false}, {"stop_requested", false}, {"requested_action", std::string("live_external_write")}};
        s.expected_route = Route::Deny;
        auto r = simulate_case(candidate, s);
        assert(r.actual_route == Route::Deny);
        assert(!r.policy_violation);
    }

    {
        ScenarioCase s;
        s.id = "unknown";
        s.family = "unknown_condition";
        s.variables = {{"request_present", true}, {"context_ready", std::monostate{}}, {"risk_high", false}, {"stop_requested", false}};
        s.expected_route = Route::Hold;
        auto r = simulate_case(candidate, s);
        assert(r.actual_route == Route::Hold);
    }

    {
        SelectionResult sel;
        sel.protocol_candidate_ref = candidate.id;
        sel.primary_archive = Archive::Elite;
        sel.archive_memberships = {Archive::Elite};
        auto p = route_promotion(candidate, sel, std::nullopt, 2, 3);
        assert(p.decision == PromotionDecision::Hold);
    }

    {
        SelectionResult sel;
        sel.protocol_candidate_ref = candidate.id;
        sel.primary_archive = Archive::Elite;
        sel.archive_memberships = {Archive::Elite};
        EvidenceManifest evidence;
        evidence.protocol_candidate_ref = candidate.id;
        evidence.source_diversity = 2;
        evidence.monitoring_defined = true;
        evidence.rollback_defined = true;
        evidence.approval_present = true;
        evidence.approval_status = "approved";
        evidence.authority_scope = "shadow_only";
        auto p = route_promotion(candidate, sel, evidence, 2, 3);
        assert(p.decision == PromotionDecision::Promote);
        auto receipt = shadow_execute(candidate, p, {{"safe_lookup", true}});
        assert(receipt.status == "shadowed");
        assert(receipt.external_effects.empty());
    }

    std::cout << "All tests passed\n";
    return 0;
}
