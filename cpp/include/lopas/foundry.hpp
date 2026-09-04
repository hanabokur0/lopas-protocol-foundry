#pragma once

#include "lopas/types.hpp"
#include <filesystem>
#include <optional>
#include <vector>

namespace lopas {

std::vector<Proxy> build_proxies(const std::vector<Observation>& observations);
std::vector<ProtocolCandidate> build_candidates(const std::vector<Proxy>& proxies);
std::vector<ScenarioCase> generate_scenarios(const ProtocolCandidate& candidate, int requested_count);
EngineResult simulate_case(const ProtocolCandidate& candidate, const ScenarioCase& scenario);
SimulationReceipt grade_case(const ProtocolCandidate& candidate, const ScenarioCase& scenario, const EngineResult& result);
SelectionResult select_candidate(const ProtocolCandidate& candidate, const std::vector<SimulationReceipt>& receipts, const SelectionThresholds& thresholds = {});
Promotion route_promotion(const ProtocolCandidate& candidate, const SelectionResult& selection, const std::optional<EvidenceManifest>& evidence, int current_level, int next_level);
ShadowActionReceipt shadow_execute(const ProtocolCandidate& candidate, const Promotion& promotion, const std::vector<AdapterBinding>& bindings);

} // namespace lopas
