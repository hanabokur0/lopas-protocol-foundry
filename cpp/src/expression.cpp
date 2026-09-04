#include "lopas/expression.hpp"

#include <algorithm>
#include <cctype>
#include <charconv>
#include <regex>

namespace lopas {
namespace {

std::string trim(std::string s) {
    auto not_space = [](unsigned char c) { return !std::isspace(c); };
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), not_space));
    s.erase(std::find_if(s.rbegin(), s.rend(), not_space).base(), s.end());
    return s;
}

std::optional<double> parse_number(const std::string& text) {
    try {
        size_t pos = 0;
        const double v = std::stod(text, &pos);
        if (pos == text.size()) return v;
    } catch (...) {
    }
    return std::nullopt;
}

Value parse_literal(std::string token) {
    token = trim(std::move(token));
    if (token == "true") return true;
    if (token == "false") return false;
    if (token == "null") return std::monostate{};
    if (token.size() >= 2 && ((token.front() == '\'' && token.back() == '\'') || (token.front() == '"' && token.back() == '"'))) {
        return token.substr(1, token.size() - 2);
    }
    if (auto n = parse_number(token)) return *n;
    return token;
}

bool equal_values(const Value& a, const Value& b) {
    if (a.index() != b.index()) return false;
    return a == b;
}

} // namespace

Evaluation evaluate_expression(const std::string& expression, const Variables& variables) {
    static const std::regex pattern(R"(^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$)");
    std::smatch match;
    if (!std::regex_match(expression, match, pattern)) {
        return {false, std::nullopt, "Unsupported expression syntax; conservative HOLD required."};
    }

    const std::string name = match[1].str();
    const std::string op = match[2].str();
    const Value rhs = parse_literal(match[3].str());
    const auto it = variables.find(name);
    if (it == variables.end() || std::holds_alternative<std::monostate>(it->second)) {
        return {true, std::nullopt, "Variable '" + name + "' is unknown."};
    }

    const Value& lhs = it->second;
    if (op == "==" || op == "!=") {
        const bool eq = equal_values(lhs, rhs);
        return {true, op == "==" ? eq : !eq, "Expression evaluated deterministically."};
    }

    if (!std::holds_alternative<double>(lhs) || !std::holds_alternative<double>(rhs)) {
        return {false, std::nullopt, "Ordered comparison requires numeric operands."};
    }
    const double a = std::get<double>(lhs);
    const double b = std::get<double>(rhs);
    bool value = false;
    if (op == ">") value = a > b;
    else if (op == "<") value = a < b;
    else if (op == ">=") value = a >= b;
    else if (op == "<=") value = a <= b;
    return {true, value, "Expression evaluated deterministically."};
}

} // namespace lopas
