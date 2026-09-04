#include "lopas/io.hpp"

#include <json-c/json.h>
#include <fstream>
#include <iomanip>
#include <memory>
#include <sstream>
#include <stdexcept>

namespace lopas::io {
namespace {

using JsonPtr = std::unique_ptr<json_object, decltype(&json_object_put)>;

JsonPtr load_json(const std::filesystem::path& path) {
    json_object* raw = json_object_from_file(path.string().c_str());
    if (!raw) throw std::runtime_error("Failed to parse JSON: " + path.string());
    return JsonPtr(raw, &json_object_put);
}

json_object* field(json_object* obj, const char* name) {
    json_object* value = nullptr;
    return json_object_object_get_ex(obj, name, &value) ? value : nullptr;
}

std::string str_field(json_object* obj, const char* name, std::string fallback = {}) {
    if (auto* v = field(obj, name); v && json_object_is_type(v, json_type_string)) return json_object_get_string(v);
    return fallback;
}

bool bool_field(json_object* obj, const char* name, bool fallback = false) {
    if (auto* v = field(obj, name); v && json_object_is_type(v, json_type_boolean)) return json_object_get_boolean(v);
    return fallback;
}

double double_field(json_object* obj, const char* name, double fallback = 0.0) {
    if (auto* v = field(obj, name); v && (json_object_is_type(v, json_type_double) || json_object_is_type(v, json_type_int))) return json_object_get_double(v);
    return fallback;
}

int int_field(json_object* obj, const char* name, int fallback = 0) {
    if (auto* v = field(obj, name); v && json_object_is_type(v, json_type_int)) return json_object_get_int(v);
    return fallback;
}

std::string esc(const std::string& input) {
    std::ostringstream out;
    for (unsigned char c : input) {
        switch (c) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (c < 0x20) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c) << std::dec;
                else out << c;
        }
    }
    return out.str();
}

void ensure_parent(const std::filesystem::path& path) {
    if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
}

std::ofstream open_out(const std::filesystem::path& path) {
    ensure_parent(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Failed to open output: " + path.string());
    return out;
}

template <typename Fn>
void write_array(const std::filesystem::path& path, std::size_t count, Fn fn) {
    auto out = open_out(path);
    out << "[\n";
    for (std::size_t i = 0; i < count; ++i) {
        out << "  ";
        fn(out, i);
        if (i + 1 != count) out << ',';
        out << '\n';
    }
    out << "]\n";
}

} // namespace

std::vector<Observation> load_observations_json(const std::filesystem::path& path) {
    auto root = load_json(path);
    json_object* array = root.get();
    if (json_object_is_type(array, json_type_object)) {
        if (auto* nested = field(array, "observations")) array = nested;
    }
    if (!json_object_is_type(array, json_type_array)) throw std::runtime_error("Observation input must be a JSON array or {observations:[...]}");

    std::vector<Observation> out;
    const auto n = json_object_array_length(array);
    for (size_t i = 0; i < n; ++i) {
        auto* item = json_object_array_get_idx(array, i);
        if (!item || !json_object_is_type(item, json_type_object)) throw std::runtime_error("Observation item must be an object");
        Observation obs;
        obs.id = str_field(item, "id");
        obs.task_type = str_field(item, "task_type", "unknown");
        obs.summary = str_field(item, "summary");
        obs.source_ref = str_field(item, "source_ref", "unknown-source");
        obs.external_impact = bool_field(item, "external_impact", false);
        obs.reversible = bool_field(item, "reversible", true);
        obs.confidence = double_field(item, "confidence", 0.5);
        if (obs.id.empty() || obs.summary.empty()) throw std::runtime_error("Each observation requires non-empty id and summary");
        out.push_back(std::move(obs));
    }
    return out;
}

std::optional<EvidenceManifest> load_evidence_json(const std::filesystem::path& path, const std::string& candidate_ref) {
    auto root = load_json(path);
    json_object* array = root.get();
    if (!json_object_is_type(array, json_type_array)) throw std::runtime_error("Evidence input must be a JSON array");
    const auto n = json_object_array_length(array);
    for (size_t i = 0; i < n; ++i) {
        auto* item = json_object_array_get_idx(array, i);
        if (!item) continue;
        if (str_field(item, "protocol_candidate_ref") != candidate_ref) continue;
        EvidenceManifest e;
        e.protocol_candidate_ref = candidate_ref;
        e.source_diversity = int_field(item, "source_diversity", 0);
        e.monitoring_defined = bool_field(item, "monitoring_defined", false);
        e.rollback_defined = bool_field(item, "rollback_defined", false);
        e.authority_scope = str_field(item, "authority_scope", "unknown");
        if (auto* approval = field(item, "approval"); approval && json_object_is_type(approval, json_type_object)) {
            e.approval_status = str_field(approval, "status", "unknown");
            e.approval_present = true;
        }
        return e;
    }
    return std::nullopt;
}

std::vector<AdapterBinding> load_bindings_json(const std::filesystem::path& path) {
    auto root = load_json(path);
    json_object* array = root.get();
    if (!json_object_is_type(array, json_type_array)) throw std::runtime_error("Bindings input must be a JSON array");
    std::vector<AdapterBinding> out;
    const auto n = json_object_array_length(array);
    for (size_t i = 0; i < n; ++i) {
        auto* item = json_object_array_get_idx(array, i);
        if (!item) continue;
        out.push_back({str_field(item, "action"), bool_field(item, "enabled", false)});
    }
    return out;
}

void write_observations(const std::filesystem::path& path, const std::vector<Observation>& items) {
    write_array(path, items.size(), [&](auto& out, size_t i) {
        const auto& x = items[i];
        out << "{\"id\":\"" << esc(x.id) << "\",\"task_type\":\"" << esc(x.task_type) << "\",\"summary\":\"" << esc(x.summary) << "\",\"source_ref\":\"" << esc(x.source_ref) << "\",\"external_impact\":" << (x.external_impact?"true":"false") << ",\"reversible\":" << (x.reversible?"true":"false") << ",\"confidence\":" << x.confidence << "}";
    });
}

void write_proxies(const std::filesystem::path& path, const std::vector<Proxy>& items) {
    write_array(path, items.size(), [&](auto& out, size_t i) {
        const auto& x = items[i];
        out << "{\"id\":\"" << esc(x.id) << "\",\"observation_ref\":\"" << esc(x.observation_ref) << "\",\"task_type\":\"" << esc(x.task_type) << "\",\"cluster_id\":\"" << esc(x.cluster_id) << "\",\"friction\":\"" << esc(x.friction) << "\",\"confidence\":" << x.confidence << ",\"risk_hints\":[";
        for (size_t j=0;j<x.risk_hints.size();++j){ if(j)out<<','; out<<"\""<<esc(x.risk_hints[j])<<"\""; }
        out << "]}";
    });
}

void write_candidates(const std::filesystem::path& path, const std::vector<ProtocolCandidate>& items) {
    write_array(path, items.size(), [&](auto& out, size_t i) {
        const auto& x = items[i];
        out << "{\"id\":\"" << esc(x.id) << "\",\"cluster_id\":\"" << esc(x.cluster_id) << "\",\"intent\":{\"status\":\"" << esc(x.intent_status) << "\"},\"routing\":{\"default\":\"" << to_string(x.default_route) << "\"},\"safety\":{\"authority_scope\":\"" << esc(x.authority_scope) << "\",\"required_human_review\":" << (x.required_human_review?"true":"false") << "},\"required_simulations\":" << x.required_simulations << ",\"provenance_refs\":[";
        for(size_t j=0;j<x.provenance_refs.size();++j){if(j)out<<',';out<<"\""<<esc(x.provenance_refs[j])<<"\"";}
        out << "]}";
    });
}

void write_simulation_receipts(const std::filesystem::path& path, const std::vector<SimulationReceipt>& items) {
    write_array(path, items.size(), [&](auto& out, size_t i) {
        const auto& x=items[i];
        out << "{\"protocol_candidate_ref\":\""<<esc(x.protocol_candidate_ref)<<"\",\"scenario_id\":\""<<esc(x.scenario_id)<<"\",\"scenario_family\":\""<<esc(x.scenario_family)<<"\",\"routing\":{\"expected\":\""<<to_string(x.expected_route)<<"\",\"actual\":\""<<to_string(x.actual_route)<<"\",\"matched\":"<<(x.route_matched?"true":"false")<<"},\"verdict\":\""<<to_string(x.verdict)<<"\",\"archive_recommendation\":\""<<to_string(x.archive_recommendation)<<"\",\"supported\":"<<(x.supported?"true":"false")<<",\"metrics\":{\"safety\":"<<x.metrics.safety<<",\"completion\":"<<x.metrics.completion<<",\"explainability\":"<<x.metrics.explainability<<",\"human_work_reduction\":"<<x.metrics.human_work_reduction<<",\"novelty\":"<<x.metrics.novelty<<",\"confidence\":"<<x.metrics.confidence<<"}}";
    });
}

void write_selection(const std::filesystem::path& path, const std::vector<SelectionResult>& items) {
    write_array(path, items.size(), [&](auto& out, size_t i) {
        const auto& x=items[i];
        out << "{\"protocol_candidate_ref\":\""<<esc(x.protocol_candidate_ref)<<"\",\"coverage\":{\"receipt_count\":"<<x.receipt_count<<",\"scenario_family_count\":"<<x.scenario_family_count<<",\"complete\":"<<(x.coverage_complete?"true":"false")<<"},\"rates\":{\"acceptable\":"<<x.acceptable_rate<<",\"reject\":"<<x.reject_rate<<",\"inconclusive\":"<<x.inconclusive_rate<<",\"route_mismatch\":"<<x.route_mismatch_rate<<"},\"metrics_mean\":{\"safety\":"<<x.mean_safety<<",\"explainability\":"<<x.mean_explainability<<",\"confidence\":"<<x.mean_confidence<<",\"human_work_reduction\":"<<x.mean_human_work_reduction<<",\"novelty\":"<<x.mean_novelty<<"},\"score\":{\"overall\":"<<x.overall_score<<"},\"classification\":{\"primary_archive\":\""<<to_string(x.primary_archive)<<"\",\"archive_memberships\":[";
        for(size_t j=0;j<x.archive_memberships.size();++j){if(j)out<<',';out<<"\""<<to_string(x.archive_memberships[j])<<"\"";}
        out << "]}}";
    });
}

void write_promotions(const std::filesystem::path& path, const std::vector<Promotion>& items) {
    write_array(path, items.size(), [&](auto& out, size_t i) {
        const auto& x=items[i];
        out << "{\"protocol_candidate_ref\":\""<<esc(x.protocol_candidate_ref)<<"\",\"decision\":\""<<to_string(x.decision)<<"\",\"eligible\":"<<(x.eligible?"true":"false")<<",\"current_level\":"<<x.current_level<<",\"next_level\":"<<x.next_level<<",\"reasons\":[";
        for(size_t j=0;j<x.reasons.size();++j){if(j)out<<',';out<<"\""<<esc(x.reasons[j])<<"\"";}
        out << "]}";
    });
}

void write_shadow_receipts(const std::filesystem::path& path, const std::vector<ShadowActionReceipt>& items) {
    write_array(path, items.size(), [&](auto& out, size_t i) {
        const auto& x=items[i];
        out << "{\"protocol_candidate_ref\":\""<<esc(x.protocol_candidate_ref)<<"\",\"route\":\""<<to_string(x.route)<<"\",\"status\":\""<<esc(x.status)<<"\",\"external_effects\":[],\"steps\":[";
        for(size_t j=0;j<x.steps.size();++j){if(j)out<<',';out<<"\""<<esc(x.steps[j])<<"\"";}
        out << "],\"reasons\":[";
        for(size_t j=0;j<x.reasons.size();++j){if(j)out<<',';out<<"\""<<esc(x.reasons[j])<<"\"";}
        out << "]}";
    });
}

} // namespace lopas::io
