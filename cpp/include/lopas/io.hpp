#pragma once

#include "lopas/types.hpp"
#include <filesystem>
#include <optional>
#include <vector>

namespace lopas::io {

std::vector<Observation> load_observations_json(const std::filesystem::path& path);
std::optional<EvidenceManifest> load_evidence_json(const std::filesystem::path& path, const std::string& candidate_ref);
std::vector<AdapterBinding> load_bindings_json(const std::filesystem::path& path);

void write_observations(const std::filesystem::path& path, const std::vector<Observation>& items);
void write_proxies(const std::filesystem::path& path, const std::vector<Proxy>& items);
void write_candidates(const std::filesystem::path& path, const std::vector<ProtocolCandidate>& items);
void write_simulation_receipts(const std::filesystem::path& path, const std::vector<SimulationReceipt>& items);
void write_selection(const std::filesystem::path& path, const std::vector<SelectionResult>& items);
void write_promotions(const std::filesystem::path& path, const std::vector<Promotion>& items);
void write_shadow_receipts(const std::filesystem::path& path, const std::vector<ShadowActionReceipt>& items);

} // namespace lopas::io
