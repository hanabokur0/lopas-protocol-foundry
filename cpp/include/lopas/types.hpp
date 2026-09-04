#pragma once

#include <map>
#include <optional>
#include <string>
#include <variant>
#include <vector>

namespace lopas {

enum class Route { Auto, Review, Hold, Escalate, Deny };
enum class Verdict { Pass, ConditionalPass, Revise, Reject, Inconclusive };
enum class Archive { None, Elite, Rare, Anomaly, Reject };
enum class PromotionDecision { Promote, Hold, Revise, Reject, Deny };

using Value = std::variant<std::monostate, bool, double, std::string>;
using Variables = std::map<std::string, Value>;

std::string to_string(Route value);
std::string to_string(Verdict value);
std::string to_string(Archive value);
std::string to_string(PromotionDecision value);
int route_priority(Route value);

struct Observation {
    std::string id;
    std::string task_type;
    std::string summary;
    std::string source_ref;
    bool external_impact{false};
    bool reversible{true};
    double confidence{0.5};
};

struct Proxy {
    std::string id;
    std::string observation_ref;
    std::string task_type;
    std::string cluster_id;
    std::string friction;
    std::vector<std::string> risk_hints;
    double confidence{0.5};
};

struct Condition {
    std::string expression;
    std::string description;
    Route on_unknown{Route::Hold};
};

struct RoutingRule {
    Condition when;
    Route route{Route::Hold};
    std::string reason;
};

struct Step {
    std::string id;
    std::string executor; // rule/tool/llm/external_system/hybrid/human
    std::string action;
};

struct KnownFailure {
    std::string code;
    Route route{Route::Hold};
};

struct ProtocolCandidate {
    std::string id;
    std::string cluster_id;
    std::string intent_status{"unconfirmed"};
    std::vector<Condition> trigger_conditions;
    std::vector<Condition> preconditions;
    std::vector<RoutingRule> routing_rules;
    Route default_route{Route::Hold};
    std::vector<Condition> stop_conditions;
    std::vector<std::string> forbidden_actions;
    bool required_human_review{true};
    std::string authority_scope{"observe_only"};
    Route failure_default_route{Route::Hold};
    std::vector<KnownFailure> known_failures;
    std::vector<Step> steps;
    std::vector<std::string> provenance_refs;
    int required_simulations{20};
};

struct RouteDecision {
    Route route{Route::Hold};
    std::string source;
    std::string reason;
    bool blocking{true};
};

struct EngineResult {
    Route actual_route{Route::Hold};
    std::string route_reason;
    bool task_completed{false};
    bool factual_error{false};
    bool policy_violation{false};
    bool receipt_complete{true};
    bool supported{true};
    std::vector<RouteDecision> decisions;
    std::vector<std::string> unsupported_expressions;
};

struct ScenarioCase {
    std::string id;
    std::string family;
    Variables variables;
    Route expected_route{Route::Hold};
    bool expected_task_completed{false};
};

struct Divergence {
    std::string type;
    std::string severity;
    std::string summary;
};

struct Metrics {
    double completion{0.0};
    double safety{0.0};
    double explainability{0.0};
    double human_work_reduction{0.0};
    double novelty{0.0};
    double confidence{0.0};
};

struct SimulationReceipt {
    std::string protocol_candidate_ref;
    std::string scenario_id;
    std::string scenario_family;
    Route expected_route{Route::Hold};
    Route actual_route{Route::Hold};
    bool route_matched{false};
    bool task_completed{false};
    bool policy_violation{false};
    bool factual_error{false};
    bool supported{true};
    Verdict verdict{Verdict::Inconclusive};
    Archive archive_recommendation{Archive::None};
    Metrics metrics;
    std::vector<Divergence> divergences;
    std::vector<std::string> failures;
};

struct SelectionThresholds {
    int minimum_receipts{12};
    int minimum_scenario_families{6};
    double elite_minimum_score{0.84};
    double elite_minimum_acceptable_rate{0.90};
    double elite_minimum_safety{0.90};
    double elite_maximum_route_mismatch{0.05};
    double rare_minimum_distance{0.18};
    double rare_minimum_novelty{0.25};
    double anomaly_minimum_family_safety_spread{0.30};
    double anomaly_minimum_inconclusive_rate{0.10};
    double reject_minimum_safety{0.70};
    double reject_maximum_route_mismatch{0.25};
    double reject_maximum_reject_rate{0.20};
};

struct SelectionResult {
    std::string protocol_candidate_ref;
    int receipt_count{0};
    int scenario_family_count{0};
    double acceptable_rate{0.0};
    double reject_rate{0.0};
    double inconclusive_rate{0.0};
    double route_mismatch_rate{0.0};
    double mean_safety{0.0};
    double mean_explainability{0.0};
    double mean_confidence{0.0};
    double mean_human_work_reduction{0.0};
    double mean_novelty{0.0};
    int policy_violation_count{0};
    int factual_error_count{0};
    int critical_route_divergence_count{0};
    int unsupported_expression_count{0};
    double family_safety_spread{0.0};
    double nearest_distance{0.0};
    double overall_score{0.0};
    bool coverage_complete{false};
    Archive primary_archive{Archive::None};
    std::vector<Archive> archive_memberships;
};

struct EvidenceManifest {
    std::string protocol_candidate_ref;
    int source_diversity{0};
    bool monitoring_defined{false};
    bool rollback_defined{false};
    bool approval_present{false};
    std::string approval_status{"unknown"};
    std::string authority_scope{"unknown"};
};

struct Promotion {
    std::string protocol_candidate_ref;
    PromotionDecision decision{PromotionDecision::Hold};
    int current_level{1};
    int next_level{2};
    bool eligible{false};
    std::vector<std::string> reasons;
};

struct AdapterBinding {
    std::string action;
    bool enabled{false};
};

struct ShadowActionReceipt {
    std::string protocol_candidate_ref;
    Route route{Route::Hold};
    std::string status{"blocked"};
    std::vector<std::string> external_effects;
    std::vector<std::string> steps;
    std::vector<std::string> reasons;
};

} // namespace lopas
