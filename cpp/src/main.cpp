#include "lopas/foundry.hpp"
#include "lopas/io.hpp"

#include <filesystem>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

struct Options {
    fs::path input;
    fs::path output_dir{"receipts/cpp_run"};
    std::optional<fs::path> evidence;
    std::optional<fs::path> bindings;
    int scenario_count{20};
    int current_level{1};
    int next_level{2};
    bool confirm_intent{false};
};

Options parse(int argc, char** argv) {
    if (argc < 2) throw std::runtime_error("Usage: lopas_foundry <observations.json> [--output-dir DIR] [--scenario-count N] [--evidence FILE] [--confirm-intent] [--current-level N] [--next-level N] [--shadow-bindings FILE]");
    Options o;
    o.input = argv[1];
    for (int i = 2; i < argc; ++i) {
        std::string arg = argv[i];
        auto need = [&](const char* name) -> std::string { if (i + 1 >= argc) throw std::runtime_error(std::string("Missing value for ") + name); return argv[++i]; };
        if (arg == "--output-dir") o.output_dir = need("--output-dir");
        else if (arg == "--scenario-count") o.scenario_count = std::stoi(need("--scenario-count"));
        else if (arg == "--evidence") o.evidence = fs::path(need("--evidence"));
        else if (arg == "--shadow-bindings") o.bindings = fs::path(need("--shadow-bindings"));
        else if (arg == "--current-level") o.current_level = std::stoi(need("--current-level"));
        else if (arg == "--next-level") o.next_level = std::stoi(need("--next-level"));
        else if (arg == "--confirm-intent") o.confirm_intent = true;
        else throw std::runtime_error("Unknown argument: " + arg);
    }
    return o;
}

int main(int argc, char** argv) {
    try {
        auto options = parse(argc, argv);
        fs::create_directories(options.output_dir);

        auto observations = lopas::io::load_observations_json(options.input);
        lopas::io::write_observations(options.output_dir / "01_observations.json", observations);

        auto proxies = lopas::build_proxies(observations);
        lopas::io::write_proxies(options.output_dir / "02_proxies.json", proxies);

        auto candidates = lopas::build_candidates(proxies);
        if (options.confirm_intent) for (auto& c : candidates) c.intent_status = "confirmed";
        lopas::io::write_candidates(options.output_dir / "03_protocol_candidates.json", candidates);

        std::vector<lopas::SimulationReceipt> all_receipts;
        std::vector<lopas::SelectionResult> selections;
        std::vector<lopas::Promotion> promotions;
        std::vector<lopas::ShadowActionReceipt> shadows;

        for (const auto& candidate : candidates) {
            auto scenarios = lopas::generate_scenarios(candidate, options.scenario_count);
            std::vector<lopas::SimulationReceipt> candidate_receipts;
            for (const auto& scenario : scenarios) {
                auto engine = lopas::simulate_case(candidate, scenario);
                auto receipt = lopas::grade_case(candidate, scenario, engine);
                all_receipts.push_back(receipt);
                candidate_receipts.push_back(std::move(receipt));
            }
            auto selection = lopas::select_candidate(candidate, candidate_receipts);
            selections.push_back(selection);

            std::optional<lopas::EvidenceManifest> evidence;
            if (options.evidence) evidence = lopas::io::load_evidence_json(*options.evidence, candidate.id);
            auto promotion = lopas::route_promotion(candidate, selection, evidence, options.current_level, options.next_level);
            promotions.push_back(promotion);

            if (options.bindings) {
                auto bindings = lopas::io::load_bindings_json(*options.bindings);
                shadows.push_back(lopas::shadow_execute(candidate, promotion, bindings));
            }
        }

        lopas::io::write_simulation_receipts(options.output_dir / "04_simulation_receipts.json", all_receipts);
        lopas::io::write_selection(options.output_dir / "05_selection_results.json", selections);
        lopas::io::write_promotions(options.output_dir / "06_poc_promotions.json", promotions);
        if (options.bindings) lopas::io::write_shadow_receipts(options.output_dir / "07_action_receipts.json", shadows);

        std::cout << "LoPAS Protocol Foundry C++ run complete\n";
        std::cout << "  observations: " << observations.size() << "\n";
        std::cout << "  candidates:   " << candidates.size() << "\n";
        std::cout << "  simulations:  " << all_receipts.size() << "\n";
        for (const auto& p : promotions) std::cout << "  " << p.protocol_candidate_ref << " => " << lopas::to_string(p.decision) << "\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
