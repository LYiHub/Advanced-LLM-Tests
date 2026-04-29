"""
Calculation engine with rule tampering overlay.
Tamper rules are stored in memory — they reset on server restart.
"""

import re

# In-memory tamper rules: dict of "a op b" → override_result
# Also maintains an auto-increment ID for API display
_tamper_rules: dict[int, dict] = {}
_tamper_rule_counter: int = 0


OPERATOR_MAP = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b if b != 0 else float("inf"),
}

OP_SYMBOLS = {"+": "+", "-": "−", "*": "×", "/": "÷"}


def normalize_expression(a, op, b):
    """
    Normalize a calculation into a canonical string key for tamper rule lookup.
    Uses standard operator symbols (+, -, *, /).
    Also tries the display symbols.
    """
    op_clean = op.strip()
    # Normalize display symbols to standard
    std_op = {"+": "+", "-": "-", "×": "*", "÷": "/", "*": "*", "/": "/"}.get(op_clean, op_clean)

    try:
        a_num = float(a)
        b_num = float(b)
    except (ValueError, TypeError):
        return None, None, None, "Invalid numbers"

    return a_num, std_op, b_num, None


def calculate(a, op, b):
    """
    Perform a calculation. Returns (result, tampered, error).
    - result: the computed (or overridden) result
    - tampered: True if the result was overridden by a tamper rule
    - error: None on success, error string on failure
    """
    a_num, std_op, b_num, err = normalize_expression(a, op, b)
    if err:
        return None, False, err

    if std_op not in OPERATOR_MAP:
        return None, False, f"Unknown operator: {op}"

    # Check tamper rules first
    overridden = check_tamper_rule(a_num, std_op, b_num)
    if overridden is not None:
        return overridden, True, None

    # Normal calculation
    try:
        result = OPERATOR_MAP[std_op](a_num, b_num)
        return result, False, None
    except ZeroDivisionError:
        return None, False, "Division by zero"


# ── Tamper rule management (in-memory) ──

def check_tamper_rule(a, op, b):
    """Check if a calculation matches a tamper rule. Returns override value or None."""
    for rule in _tamper_rules.values():
        # Compare with tolerance for floating point
        if abs(rule["a"] - a) < 1e-10 and rule["op"] == op and abs(rule["b"] - b) < 1e-10:
            return rule["result"]
    return None


def add_tamper_rule(a, op, b, result):
    """Add a tamper rule. Returns the rule dict with ID."""
    global _tamper_rule_counter
    a_num, std_op, b_num, err = normalize_expression(a, op, b)
    if err:
        return None, err

    try:
        result_num = float(result)
    except (ValueError, TypeError):
        return None, "Invalid result value"

    _tamper_rule_counter += 1
    rule = {
        "id": _tamper_rule_counter,
        "a": a_num,
        "op": std_op,
        "b": b_num,
        "result": result_num,
    }
    _tamper_rules[_tamper_rule_counter] = rule
    return rule, None


def remove_tamper_rule(rule_id):
    """Remove a tamper rule by ID. Returns True if found and removed."""
    if rule_id in _tamper_rules:
        del _tamper_rules[rule_id]
        return True
    return False


def get_tamper_rules():
    """Get all current tamper rules, sorted by ID."""
    return [r for _, r in sorted(_tamper_rules.items(), key=lambda x: x[0])]


def format_rule(rule):
    """Format a tamper rule for display."""
    op_display = OP_SYMBOLS.get(rule["op"], rule["op"])
    # Format numbers to avoid ugly floats like 2.0
    a_str = _fmt_num(rule["a"])
    b_str = _fmt_num(rule["b"])
    r_str = _fmt_num(rule["result"])
    return {
        "id": rule["id"],
        "expression": f"{a_str} {op_display} {b_str}",
        "result": rule["result"],
        "display": f"{a_str} {op_display} {b_str} = {r_str}",
    }


def _fmt_num(n):
    """Format a number nicely — int if whole, otherwise float."""
    if isinstance(n, float) and n == int(n) and n != float("inf"):
        return str(int(n))
    return str(n)
