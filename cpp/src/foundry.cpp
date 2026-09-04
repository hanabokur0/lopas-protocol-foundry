#include "lopas/foundry.hpp"
#include "lopas/expression.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <numeric>
#include <set>
#include <sstream>

namespace lopas {
namespace {

Route choose_route(Route fallback, const std::vector<RouteDecision>& decisions, std::string& reason) {
    if (decisions.empty()) {
        reason = "No override matched; candidate default route used.";
        return fallback;
    }
    const auto it = std::max_element(decisions.begin(), decisions.end(), [](const auto& a, const auto& b) {
        return route_priority(a.route) < route_priority(b.route);
    });
    reason = it->reason;
    return it->route;
}

void evaluate_conditions(const std::vector<Condition>& conditions,
                         const Variables& variables,
                         const std::string& section,
                         Route false_route,
                         std::vector<RouteDecision>& decisions,
                         std::vector<std::string>& unsupported) {
    for (const auto& condition : conditions) {
        const auto evaluation = evaluate_expression(condition.expression, variables);
        if (!evaluation.supported) {
            unsupported.push_back(condition.expression);
            decisions.push_back({Route::Hold, section, evaluation.reason, true});
        } else if (!evaluation.value.has_value()) {
            decisions.push_back({condition.on_unknown, section, condition.description + " " + evaluation.reason, true});
        } else if (!*evaluation.value) {
            decisions.push_back({false_route, section, "Condition false: " + condition.description, true});
        }
    }
}

bool variable_true(const Variables& vars, const std::string& key) {
    const auto it = vars.find(key);
    return it != vars.end() && std::holds_alternative<bool>(it->second) && std::get<bool>(it->second);
}

std::optional<std::string> variable_string(const Variables& vars, const std::string& key) {
    const auto it = vars.find(key);
    if (it == vars.end() || !std::holds_alternative<std::string>(it->second)) return std::nullopt;
    return std::get<std::string>(it->second);
}

bool is_acceptable(Verdict v) {
    return v == Verdict::Pass || v == Verdict::ConditionalPass;
}

double mean(const std::vector<double>& values) {
    if (values.empty()) return 0.0;
    return std::accumulate(values.begin(), values.end(), 0.0) / static_cast<double>(values.size());
}

double round4(double value) {
    return std::round(value * 10000.0) / 10000.0;
}

bool contains_archive(const SelectionResult& selection, Archive archive) {
    return std::find(selection.archive_memberships.begin(), selection.archive_memberships.end(), archive) != selection.archive_memberships.end();
}

} // namespace

std::vector<Proxy> build_proxies(const std::vector<Observation>& observations) {
    std::vector<Proxy> out;
    out.reserve(observations.size());
    for (const auto& obs : observations) {
        Proxy proxy;
        proxy.id = "proxy-" + obs.id;
        proxy.observation_ref = obs.id;
        proxy.task_type = obs.task_type.empty() ? "unknown" : obs.task_type;
        proxy.cluster_id = "cluster-" + proxy.task_type;
        proxy.friction = obs.summary;
        proxy.confidence = std::clamp(obs.confidence, 0.0, 1.0);
        if (obs.external_impact) proxy.risk_hints.push_back("external_impact");
        if (!obs.reversible) proxy.risk_hints.push_back("low_reversibility");
        out.push_back(std::move(proxy));
    }
    return out;
}

std::vector<ProtocolCandidate> build_candidates(const std::vector<Proxy>& proxies) {
    std::map<std::string, std::vector<const Proxy*>> grouped;
    for (const auto& proxy : proxies) grouped[proxy.cluster_id].push_back(&proxy);

    std::vector<ProtocolCandidate> out;
    for (const auto& [cluster, items] : grouped) {
        ProtocolCandidate candidate;
        candidate.id = "protocol-" + cluster;
        candidate.cluster_id = cluster;
        candidate.intent_status = "unconfirmed";
        candidate.default_route = Route::Hold;
        candidate.failure_default_route = Route::Hold;
        candidate.required_human_review = true;
        candidate.authority_scope = "observe_only";
        candidate.required_simulations = 20;
        candidate.trigger_conditions.push_back({"request_present == true", "A request must be present.", Route::Hold});
        candidate.preconditions.push_back({"context_ready == true", "Required context must be ready.", Route::Hold});
        candidate.routing_rules.push_back({{"risk_high == true", "High-risk context requires escalation.", Route::Hold}, Route::Escalate, "High-risk work is not auto-routed."});
        candidate.stop_conditions.push_back({"stop_requested == true", "A stop request halts processing.", Route::Hold});
        candidate.forbidden_actions = {"live_external_write", "credential_exfiltration"};
        candidate.known_failures.push_back({"DEPENDENCY_UNAVAILABLE", Route::Hold});
        candidate.steps.push_back({"step-1", "rule", "normalize_input"});
        candidate.steps.push_back({"step-2", "rule", "evaluate_candidate"});
        candidate.steps.push_back({"step-3", "human", "review_before_external_effect"});
        for (const auto* item : items) candidate.provenance_refs.push_back(item->observation_ref);
        out.push_back(std::move(candidate));
    }
    return out;
}

std::vector<ScenarioCase> generate_scenarios(const ProtocolCandidate& candidate, int requested_count) {
    const int count = std::max(1, requested_count);
    std::vector<ScenarioCase> base;
    auto nominal = Variables{{"request_present", true}, {"context_ready", true}, {"risk_high", false}, {"stop_requested", false}, {"human_review_approved", true}};

    base.push_back({candidate.id + "-nominal", "nominal", nominal, Route::Hold, false});

    auto missing = nominal;
    missing["missing_required_input"] = std::string("customer_id");
    base.push_back({candidate.id + "-missing-input", "missing_input", missing, Route::Hold, false});

    auto unknown = nominal;
    unknown["context_ready"] = std::monostate{};
    base.push_back({candidate.id + "-unknown-condition", "unknown_condition", unknown, Route::Hold, false});

    auto false_condition = nominal;
    false_condition["context_ready"] = false;
    base.push_back({candidate.id + "-false-condition", "false_condition", false_condition, Route::Hold, false});

    auto human_review = nominal;
    human_review.erase("human_review_approved");
    base.push_back({candidate.id + "-human-review", "human_review", human_review, Route::Review, false});

    auto risky = nominal;
    risky["risk_high"] = true;
    base.push_back({candidate.id + "-risk", "routing_rule", risky, Route::Escalate, false});

    auto stop = nominal;
    stop["stop_requested"] = true;
    base.push_back({candidate.id + "-stop", "stop_condition", stop, Route::Hold, false});

    auto forbidden = nominal;
    forbidden["requested_action"] = std::string("live_external_write");
    base.push_back({candidate.id + "-forbidden", "forbidden_action", forbidden, Route::Deny, false});

    auto failure = nominal;
    failure["forced_failure_code"] = std::string("DEPENDENCY_UNAVAILABLE");
    base.push_back({candidate.id + "-known-failure", "known_failure", failure, Route::Hold, false});

    std::vector<ScenarioCase> out;
    out.reserve(count);
    for (int i = 0; i < count; ++i) {
        ScenarioCase c = base[static_cast<size_t>(i) % base.size()];
        c.id += "-" + std::to_string(i + 1);
        out.push_back(std::move(c));
    }
    return out;
}

EngineResult simulate_case(const ProtocolCandidate& candidate, const ScenarioCase& scenario) {
    EngineResult result;
    std::vector<RouteDecision> decisions;
    std::vector<std::string> unsupported;

    const auto requested_action = variable_string(scenario.variables, "requested_action");
    if (requested_action && std::find(candidate.forbidden_actions.begin(), candidate.forbidden_actions.end(), *requested_action) != candidate.forbidden_actions.end()) {
        decisions.push_back({Route::Deny, "safety", "Requested action '" + *requested_action + "' is forbidden.", true});
    }

    if (auto missing = variable_string(scenario.variables, "missing_required_input")) {
        decisions.push_back({Route::Hold, "inputs", "Required input '" + *missing + "' is unavailable.", true});
    }

    evaluate_conditions(candidate.trigger_conditions, scenario.variables, "trigger", Route::Hold, decisions, unsupported);
    evaluate_conditions(candidate.preconditions, scenario.variables, "precondition", Route::Hold, decisions, unsupported);

    for (const auto& rule : candidate.routing_rules) {
        const auto evaluation = evaluate_expression(rule.when.expression, scenario.variables);
        if (!evaluation.supported) {
            unsupported.push_back(rule.when.expression);
            decisions.push_back({Route::Hold, "routing_rule", evaluation.reason, true});
        } else if (!evaluation.value.has_value()) {
            decisions.push_back({rule.when.on_unknown, "routing_rule", rule.when.description + " " + evaluation.reason, true});
        } else if (*evaluation.value) {
            decisions.push_back({rule.route, "routing_rule", rule.reason, rule.route != Route::Auto});
        }
    }

    for (const auto& condition : candidate.stop_conditions) {
        const auto evaluation = evaluate_expression(condition.expression, scenario.variables);
        if (!evaluation.supported) {
            unsupported.push_back(condition.expression);
            decisions.push_back({Route::Hold, "stop_condition", evaluation.reason, true});
        } else if (!evaluation.value.has_value()) {
            decisions.push_back({condition.on_unknown, "stop_condition", condition.description + " " + evaluation.reason, true});
        } else if (*evaluation.value) {
            decisions.push_back({candidate.failure_default_route, "stop_condition", "Stop condition true: " + condition.description, true});
        }
    }

    if (auto failure_code = variable_string(scenario.variables, "forced_failure_code")) {
        const auto it = std::find_if(candidate.known_failures.begin(), candidate.known_failures.end(), [&](const auto& failure) { return failure.code == *failure_code; });
        if (it != candidate.known_failures.end()) {
            decisions.push_back({it->route, "known_failure", "Known failure injected: " + *failure_code + ".", true});
        } else {
            decisions.push_back({candidate.failure_default_route, "unknown_failure", "Unknown failure injected: " + *failure_code + ".", true});
        }
    }

    if (candidate.required_human_review) {
        const auto approved_it = scenario.variables.find("human_review_approved");
        const auto rejected_it = scenario.variables.find("human_review_rejected");
        const bool rejected = rejected_it != scenario.variables.end() && std::holds_alternative<bool>(rejected_it->second) && std::get<bool>(rejected_it->second);
        if (rejected || (approved_it != scenario.variables.end() && std::holds_alternative<bool>(approved_it->second) && !std::get<bool>(approved_it->second))) {
            decisions.push_back({candidate.failure_default_route, "human_review", "Required human review rejected the result.", true});
        } else if (approved_it == scenario.variables.end() || std::holds_alternative<std::monostate>(approved_it->second)) {
            decisions.push_back({Route::Review, "human_review", "Required human review has not been completed.", true});
        }
    }

    result.actual_route = choose_route(candidate.default_route, decisions, result.route_reason);
    result.factual_error = variable_true(scenario.variables, "force_factual_error");
    result.policy_violation = requested_action && std::find(candidate.forbidden_actions.begin(), candidate.forbidden_actions.end(), *requested_action) != candidate.forbidden_actions.end() && result.actual_route != Route::Deny;
    result.supported = unsupported.empty();
    result.decisions = std::move(decisions);
    std::sort(unsupported.begin(), unsupported.end());
    unsupported.erase(std::unique(unsupported.begin(), unsupported.end()), unsupported.end());
    result.unsupported_expressions = std::move(unsupported);
    const bool blocking = std::any_of(result.decisions.begin(), result.decisions.end(), [](const auto& d) { return d.blocking; });
    result.task_completed = (result.actual_route == Route::Auto || result.actual_route == Route::Review) && !blocking && !result.factual_error && !result.policy_violation;
    return result;
}

SimulationReceipt grade_case(const ProtocolCandidate& candidate, const ScenarioCase& scenario, const EngineResult& result) {
    SimulationReceipt receipt;
    receipt.protocol_candidate_ref = candidate.id;
    receipt.scenario_id = scenario.id;
    receipt.scenario_family = scenario.family;
    receipt.expected_route = scenario.expected_route;
    receipt.actual_route = result.actual_route;
    receipt.route_matched = result.actual_route == scenario.expected_route;
    receipt.task_completed = result.task_completed;
    receipt.policy_violation = result.policy_violation;
    receipt.factual_error = result.factual_error;
    receipt.supported = result.supported;

    bool completion_matched = result.task_completed == scenario.expected_task_completed;
    if (!receipt.route_matched) {
        const bool less_conservative = route_priority(result.actual_route) < route_priority(scenario.expected_route);
        receipt.divergences.push_back({"route", less_conservative ? "critical" : "medium", "The deterministic simulator selected a different route from the scenario expectation."});
    }
    if (!completion_matched) receipt.divergences.push_back({"output", "high", "Task-completion behavior differed from the scenario expectation."});
    if (result.policy_violation) receipt.divergences.push_back({"safety", "critical", "A forbidden action was not denied."});
    for (const auto& expression : result.unsupported_expressions) receipt.failures.push_back("UNSUPPORTED_EXPRESSION: " + expression);

    if (result.policy_violation) {
        receipt.verdict = Verdict::Reject;
        receipt.archive_recommendation = Archive::Reject;
    } else if (!result.supported) {
        receipt.verdict = Verdict::Inconclusive;
        receipt.archive_recommendation = Archive::Anomaly;
    } else if (!receipt.route_matched) {
        const bool less_conservative = route_priority(result.actual_route) < route_priority(scenario.expected_route);
        receipt.verdict = less_conservative ? Verdict::Reject : Verdict::Revise;
        receipt.archive_recommendation = less_conservative ? Archive::Reject : Archive::Anomaly;
    } else if (!completion_matched) {
        receipt.verdict = Verdict::Revise;
        receipt.archive_recommendation = Archive::Anomaly;
    } else if (result.task_completed) {
        receipt.verdict = Verdict::Pass;
    } else {
        receipt.verdict = Verdict::ConditionalPass;
    }

    const std::set<std::string> executors = [&] {
        std::set<std::string> s;
        for (const auto& step : candidate.steps) s.insert(step.executor);
        return s;
    }();
    std::set<Route> routes{candidate.default_route};
    for (const auto& rule : candidate.routing_rules) routes.insert(rule.route);
    double novelty = 0.10 + std::min(0.30, 0.08 * static_cast<double>(executors.size())) + std::min(0.25, 0.05 * static_cast<double>(routes.size()));
    if (candidate.authority_scope == "observe_only") novelty += 0.10;
    novelty = std::min(1.0, novelty);

    std::map<std::string, double> weights{{"rule", 1.0}, {"tool", 1.0}, {"llm", 1.0}, {"external_system", 1.0}, {"hybrid", 0.5}, {"human", 0.0}};
    double hwr = 0.0;
    for (const auto& step : candidate.steps) hwr += weights[step.executor];
    if (!candidate.steps.empty()) hwr /= static_cast<double>(candidate.steps.size());
    if (!result.task_completed) hwr *= 0.25;

    double safety = 0.0;
    if (result.policy_violation) safety = 0.0;
    else if (scenario.expected_route == result.actual_route) safety = 1.0;
    else if (route_priority(result.actual_route) > route_priority(scenario.expected_route)) safety = 0.88;
    else safety = 0.30;

    receipt.metrics.completion = result.task_completed ? 1.0 : 0.0;
    receipt.metrics.safety = safety;
    receipt.metrics.explainability = receipt.route_matched ? 0.95 : 0.68;
    receipt.metrics.human_work_reduction = std::round(hwr * 1000.0) / 1000.0;
    receipt.metrics.novelty = std::round(novelty * 1000.0) / 1000.0;
    receipt.metrics.confidence = result.supported ? 0.97 : 0.62;
    return receipt;
}

SelectionResult select_candidate(const ProtocolCandidate& candidate, const std::vector<SimulationReceipt>& receipts, const SelectionThresholds& t) {
    SelectionResult result;
    result.protocol_candidate_ref = candidate.id;
    result.receipt_count = static_cast<int>(receipts.size());
    std::set<std::string> families;
    std::vector<double> safety, explainability, confidence, hwr, novelty;
    std::map<std::string, std::vector<double>> family_safety;
    int acceptable = 0, reject = 0, inconclusive = 0, mismatch = 0;
    int policy = 0, factual = 0, critical = 0, unsupported = 0;

    for (const auto& r : receipts) {
        families.insert(r.scenario_family);
        if (is_acceptable(r.verdict)) ++acceptable;
        if (r.verdict == Verdict::Reject) ++reject;
        if (r.verdict == Verdict::Inconclusive) ++inconclusive;
        if (!r.route_matched) ++mismatch;
        if (r.policy_violation) ++policy;
        if (r.factual_error) ++factual;
        unsupported += static_cast<int>(r.failures.size());
        for (const auto& d : r.divergences) if (d.type == "route" && d.severity == "critical") ++critical;
        safety.push_back(r.metrics.safety);
        explainability.push_back(r.metrics.explainability);
        confidence.push_back(r.metrics.confidence);
        hwr.push_back(r.metrics.human_work_reduction);
        novelty.push_back(r.metrics.novelty);
        family_safety[r.scenario_family].push_back(r.metrics.safety);
    }

    const double n = std::max(1.0, static_cast<double>(receipts.size()));
    result.scenario_family_count = static_cast<int>(families.size());
    result.acceptable_rate = acceptable / n;
    result.reject_rate = reject / n;
    result.inconclusive_rate = inconclusive / n;
    result.route_mismatch_rate = mismatch / n;
    result.mean_safety = mean(safety);
    result.mean_explainability = mean(explainability);
    result.mean_confidence = mean(confidence);
    result.mean_human_work_reduction = mean(hwr);
    result.mean_novelty = mean(novelty);
    result.policy_violation_count = policy;
    result.factual_error_count = factual;
    result.critical_route_divergence_count = critical;
    result.unsupported_expression_count = unsupported;

    std::vector<double> family_means;
    for (const auto& [_, values] : family_safety) family_means.push_back(mean(values));
    if (!family_means.empty()) {
        const auto [mn, mx] = std::minmax_element(family_means.begin(), family_means.end());
        result.family_safety_spread = *mx - *mn;
    }

    // C++ reference port has no cross-candidate diversity graph yet; keep distance at 0.
    result.nearest_distance = 0.0;
    const double receipt_ratio = std::min(1.0, result.receipt_count / static_cast<double>(t.minimum_receipts));
    const double family_ratio = std::min(1.0, result.scenario_family_count / static_cast<double>(t.minimum_scenario_families));
    const double coverage = 0.5 * receipt_ratio + 0.5 * family_ratio;
    result.coverage_complete = receipt_ratio >= 1.0 && family_ratio >= 1.0;
    const double route_reliability = 1.0 - result.route_mismatch_rate;
    result.overall_score = round4(
        result.mean_safety * 0.30 + result.acceptable_rate * 0.20 + result.mean_explainability * 0.12 +
        route_reliability * 0.15 + result.mean_confidence * 0.08 + result.mean_human_work_reduction * 0.10 + coverage * 0.05);

    bool reject_archive = policy > 0 || factual > 0 || critical > 0 || result.mean_safety < t.reject_minimum_safety || result.route_mismatch_rate > t.reject_maximum_route_mismatch || result.reject_rate > t.reject_maximum_reject_rate;
    if (reject_archive) {
        result.primary_archive = Archive::Reject;
        result.archive_memberships = {Archive::Reject};
        return result;
    }

    const bool anomaly = unsupported > 0 || result.family_safety_spread >= t.anomaly_minimum_family_safety_spread || result.inconclusive_rate >= t.anomaly_minimum_inconclusive_rate || std::any_of(receipts.begin(), receipts.end(), [](const auto& r){ return r.archive_recommendation == Archive::Anomaly; });
    const bool elite = result.coverage_complete && result.overall_score >= t.elite_minimum_score && result.acceptable_rate >= t.elite_minimum_acceptable_rate && result.mean_safety >= t.elite_minimum_safety && result.route_mismatch_rate <= t.elite_maximum_route_mismatch;
    const bool rare = result.nearest_distance >= t.rare_minimum_distance && result.mean_novelty >= t.rare_minimum_novelty && result.receipt_count >= std::max(4, t.minimum_receipts / 2);

    if (elite) result.archive_memberships.push_back(Archive::Elite);
    if (rare) result.archive_memberships.push_back(Archive::Rare);
    if (anomaly) result.archive_memberships.push_back(Archive::Anomaly);
    result.primary_archive = anomaly ? Archive::Anomaly : (elite ? Archive::Elite : (rare ? Archive::Rare : Archive::None));
    return result;
}

Promotion route_promotion(const ProtocolCandidate& candidate, const SelectionResult& selection, const std::optional<EvidenceManifest>& evidence, int current_level, int next_level) {
    Promotion p;
    p.protocol_candidate_ref = candidate.id;
    p.current_level = current_level;
    p.next_level = next_level;

    if (candidate.intent_status == "denied") {
        p.decision = PromotionDecision::Deny;
        p.reasons.push_back("Candidate intent was explicitly denied.");
        return p;
    }
    if (selection.primary_archive == Archive::Reject || contains_archive(selection, Archive::Reject)) {
        p.decision = PromotionDecision::Reject;
        p.reasons.push_back("Selection rejected the candidate.");
        return p;
    }
    if (selection.primary_archive == Archive::Anomaly || contains_archive(selection, Archive::Anomaly)) {
        p.decision = PromotionDecision::Revise;
        p.reasons.push_back("Selection identified anomaly behavior requiring revision.");
        return p;
    }
    if (candidate.intent_status != "confirmed") p.reasons.push_back("Candidate intent is not confirmed.");
    if (!contains_archive(selection, Archive::Elite) && selection.primary_archive != Archive::Elite) p.reasons.push_back("Candidate is not in the elite archive.");
    if (next_level != current_level + 1) p.reasons.push_back("Promotion may advance only one validation level at a time.");

    if (!evidence) {
        p.reasons.push_back("Evidence manifest missing: source diversity, monitoring, rollback, authority, and approval remain unknown.");
    } else {
        if (evidence->protocol_candidate_ref != candidate.id) p.reasons.push_back("Evidence manifest references a different candidate.");
        if (evidence->source_diversity < 2) p.reasons.push_back("Verified source diversity is below 2.");
        if (!evidence->monitoring_defined) p.reasons.push_back("Monitoring is not defined.");
        if (!evidence->rollback_defined) p.reasons.push_back("Rollback/containment is not defined.");
        if (!evidence->approval_present || evidence->approval_status != "approved") p.reasons.push_back("Human approval is missing or not approved.");
        if (evidence->authority_scope == "unknown") p.reasons.push_back("Authority scope is unknown.");
    }

    if (!p.reasons.empty()) {
        p.decision = PromotionDecision::Hold;
        return p;
    }
    p.decision = PromotionDecision::Promote;
    p.eligible = true;
    p.reasons.push_back("All conservative promotion gates passed.");
    return p;
}

ShadowActionReceipt shadow_execute(const ProtocolCandidate& candidate, const Promotion& promotion, const std::vector<AdapterBinding>& bindings) {
    ShadowActionReceipt receipt;
    receipt.protocol_candidate_ref = candidate.id;
    receipt.external_effects = {};

    if (promotion.protocol_candidate_ref != candidate.id) receipt.reasons.push_back("Promotion references a different Protocol Candidate.");
    if (candidate.intent_status != "confirmed") receipt.reasons.push_back("Candidate intent is not confirmed.");
    if (promotion.decision != PromotionDecision::Promote || !promotion.eligible) receipt.reasons.push_back("Promotion is not PROMOTE/eligible.");
    if (promotion.next_level < 3) receipt.reasons.push_back("Shadow execution requires next validation level >= 3.");

    for (const auto& step : candidate.steps) {
        if (step.executor == "tool" || step.executor == "external_system") {
            const auto binding = std::find_if(bindings.begin(), bindings.end(), [&](const auto& b){ return b.action == step.action; });
            if (binding == bindings.end() || !binding->enabled) receipt.reasons.push_back("Missing or disabled Adapter Binding for action: " + step.action);
        }
        if (std::find(candidate.forbidden_actions.begin(), candidate.forbidden_actions.end(), step.action) != candidate.forbidden_actions.end()) receipt.reasons.push_back("Step action is explicitly forbidden: " + step.action);
    }

    if (!receipt.reasons.empty()) {
        receipt.route = Route::Hold;
        receipt.status = "blocked";
        return receipt;
    }

    receipt.route = Route::Auto; // READY equivalent in this typed subset.
    receipt.status = "shadowed";
    for (const auto& step : candidate.steps) receipt.steps.push_back(step.id + ": " + step.action + " [external_effect:none]");
    return receipt;
}

} // namespace lopas
