"""Binary calculator core with in-memory rule tampering.

A single calculation is a triple (a, op, b). Everything flows through
`compute()`, which consults the override table before doing real math.
"""
import threading


_lock = threading.Lock()
# Maps "a op b" string key -> {"a": float, "op": str, "b": float, "result": float}
# Stored in-memory only; cleared on every server restart per spec.
_overrides = {}


# ---------- Number parsing ----------

def parse_number(s):
    """Accept int-looking strings as int, fall back to float. Raise ValueError on junk."""
    if isinstance(s, (int, float)):
        return s
    if not isinstance(s, str):
        raise ValueError("操作数必须是数字")
    s = s.strip()
    if not s:
        raise ValueError("操作数不能为空")
    try:
        if "." in s or "e" in s or "E" in s:
            return float(s)
        return int(s)
    except ValueError:
        raise ValueError(f"无法解析数字: {s}")


def _key(a, op, b):
    # Normalize so "1 + 1" and "1.0 + 1.0" hit the same override entry.
    return f"{_normalize_num(a)} {op} {_normalize_num(b)}"


def _normalize_num(n):
    f = float(n)
    if f.is_integer():
        return str(int(f))
    return repr(f)


# ---------- Override management ----------

def set_override(a, op, b, result):
    a = parse_number(a)
    b = parse_number(b)
    result = parse_number(result)
    if op not in ("+", "-", "*", "/"):
        raise ValueError("不支持的运算符")
    key = _key(a, op, b)
    with _lock:
        _overrides[key] = {"a": a, "op": op, "b": b, "result": result}
    return key


def delete_override(key):
    with _lock:
        return _overrides.pop(key, None) is not None


def list_overrides():
    with _lock:
        items = []
        for k, v in _overrides.items():
            items.append({
                "key": k,
                "a": v["a"],
                "op": v["op"],
                "b": v["b"],
                "result": v["result"],
            })
        return items


def _lookup_override(a, op, b):
    key = _key(a, op, b)
    with _lock:
        return _overrides.get(key)


# ---------- Core compute ----------

def compute(a, op, b):
    """Return the (possibly tampered) numeric result as a Python number.

    Raises ValueError for bad input (e.g. divide-by-zero), so the caller can
    surface a clean 400 to the client.
    """
    a = parse_number(a)
    b = parse_number(b)
    if op not in ("+", "-", "*", "/"):
        raise ValueError("不支持的运算符")

    override = _lookup_override(a, op, b)
    if override is not None:
        return override["result"]

    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ValueError("除数不能为零")
        # Integer division when both sides look like ints and divide cleanly
        if isinstance(a, int) and isinstance(b, int) and a % b == 0:
            return a // b
        return a / b


def format_result(n):
    """Pretty-print so integers don't render as '4.0'."""
    if isinstance(n, bool):
        return str(n)
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if n.is_integer():
            return str(int(n))
        # Trim trailing zeros
        s = ("%.10f" % n).rstrip("0").rstrip(".")
        return s or "0"
    return str(n)
