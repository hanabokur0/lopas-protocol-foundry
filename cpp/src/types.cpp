#include "lopas/types.hpp"
#include <stdexcept>

namespace lopas {

std::string to_string(Route value) {
    switch (value) {
        case Route::Auto: return "AUTO";
        case Route::Review: return "REVIEW";
        case Route::Hold: return "HOLD";
        case Route::Escalate: return "ESCALATE";
        case Route::Deny: return "DENY";
    }
    throw std::logic_error("unknown Route");
}

std::string to_string(Verdict value) {
    switch (value) {
        case Verdict::Pass: return "pass";
        case Verdict::ConditionalPass: return "conditional_pass";
        case Verdict::Revise: return "revise";
        case Verdict::Reject: return "reject";
        case Verdict::Inconclusive: return "inconclusive";
    }
    throw std::logic_error("unknown Verdict");
}

std::string to_string(Archive value) {
    switch (value) {
        case Archive::None: return "none";
        case Archive::Elite: return "elite";
        case Archive::Rare: return "rare";
        case Archive::Anomaly: return "anomaly";
        case Archive::Reject: return "reject";
    }
    throw std::logic_error("unknown Archive");
}

std::string to_string(PromotionDecision value) {
    switch (value) {
        case PromotionDecision::Promote: return "PROMOTE";
        case PromotionDecision::Hold: return "HOLD";
        case PromotionDecision::Revise: return "REVISE";
        case PromotionDecision::Reject: return "REJECT";
        case PromotionDecision::Deny: return "DENY";
    }
    throw std::logic_error("unknown PromotionDecision");
}

int route_priority(Route value) {
    switch (value) {
        case Route::Auto: return 1;
        case Route::Review: return 2;
        case Route::Hold: return 3;
        case Route::Escalate: return 4;
        case Route::Deny: return 5;
    }
    return 0;
}

} // namespace lopas
