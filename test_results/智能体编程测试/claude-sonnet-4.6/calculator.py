"""
calculator.py - Calculation logic and math-rule-tampering engine.

Tampered rules live purely in-memory: they are reset on server restart.
"""
import math
from typing import Optional

# ──────────────────────────────────────────────
# In-memory rule store
# Key:   (operand_a, operation, operand_b)  →  overridden result (as string)
# ──────────────────────────────────────────────
_tampered_rules: dict[tuple, str] = {}


# ──────────────────────────────────────────────
# Rule management (superadmin only)
# ──────────────────────────────────────────────

def set_rule(a: float, operation: str, b: Optional[float], result: str):
    """
    Store a tampered rule.
    For unary ops (sqrt) b is None.
    """
    key = _make_key(a, operation, b)
    _tampered_rules[key] = result


def delete_rule(a: float, operation: str, b: Optional[float]) -> bool:
    """Remove a tampered rule. Returns True if it existed."""
    key = _make_key(a, operation, b)
    if key in _tampered_rules:
        del _tampered_rules[key]
        return True
    return False


def list_rules() -> list[dict]:
    """Return all active tampered rules."""
    result = []
    for (a, op, b), val in _tampered_rules.items():
        result.append({
            "a": a,
            "operation": op,
            "b": b,
            "result": val,
        })
    return result


def _make_key(a: float, operation: str, b: Optional[float]) -> tuple:
    """Normalize floats to avoid floating-point key mismatches."""
    na = _norm(a)
    nb = _norm(b) if b is not None else None
    return (na, operation, nb)


def _norm(v: float):
    """Represent the float as int if it is a whole number, for consistent key matching."""
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


# ──────────────────────────────────────────────
# Core calculation
# ──────────────────────────────────────────────

SUPPORTED_OPS = {"add", "subtract", "multiply", "divide", "power", "sqrt"}


def calculate(operation: str, a: float, b: Optional[float] = None) -> str:
    """
    Perform the calculation.
    Checks tampered rules first, then falls back to real math.
    Returns the result as a string.
    Raises ValueError for illegal operations (e.g. divide by zero).
    """
    if operation not in SUPPORTED_OPS:
        raise ValueError(f"不支持的运算: {operation}")

    # Check tamper rule
    key = _make_key(a, operation, b)
    if key in _tampered_rules:
        return _tampered_rules[key]

    # Real calculation
    return _real_calculate(operation, a, b)


def _real_calculate(operation: str, a: float, b: Optional[float]) -> str:
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("除数不能为零")
        result = a / b
    elif operation == "power":
        result = a ** b
    elif operation == "sqrt":
        if a < 0:
            raise ValueError("不能对负数开方")
        result = math.sqrt(a)
    else:
        raise ValueError(f"不支持的运算: {operation}")

    # Format: prefer integer display when result is a whole number
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(result)


def format_expression(operation: str, a: float, b: Optional[float]) -> str:
    """Return a human-readable expression string, e.g. '2 + 3'."""
    op_symbols = {
        "add":      "+",
        "subtract": "-",
        "multiply": "×",
        "divide":   "÷",
        "power":    "^",
        "sqrt":     "√",
    }
    sym = op_symbols.get(operation, operation)
    a_str = str(int(a)) if isinstance(a, float) and a.is_integer() else str(a)
    if operation == "sqrt":
        return f"√{a_str}"
    b_str = str(int(b)) if isinstance(b, float) and b.is_integer() else str(b)
    return f"{a_str} {sym} {b_str}"
