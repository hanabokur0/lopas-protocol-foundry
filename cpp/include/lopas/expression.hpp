#pragma once

#include "lopas/types.hpp"
#include <optional>
#include <string>

namespace lopas {

struct Evaluation {
    bool supported{false};
    std::optional<bool> value;
    std::string reason;
};

Evaluation evaluate_expression(const std::string& expression, const Variables& variables);

} // namespace lopas
