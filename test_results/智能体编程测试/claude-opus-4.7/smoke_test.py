"""End-to-end smoke test covering acceptance scenarios A / B / C / D.

Run against a freshly-started server (fresh calc.db):
    python server.py           # in one terminal
    python smoke_test.py       # in another

The script uses only urllib from the standard library.
"""
import json
import sys
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

BASE = "http://localhost:8080"


def client():
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return opener


def call(opener, path, method="GET", body=None, expect_ok=True):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        resp = opener.open(req, timeout=5)
        payload = json.loads(resp.read().decode("utf-8"))
        status = resp.status
    except urllib.error.HTTPError as e:
        payload = json.loads(e.read().decode("utf-8"))
        status = e.code
    if expect_ok and not payload.get("ok"):
        raise AssertionError(f"{method} {path} -> {status} {payload}")
    return status, payload


def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}: expected {b!r}, got {a!r}")


def main():
    # -------- Scenario A: role-gated buttons --------
    print("Scenario A: role permission isolation")
    alice = client()
    # Register alice (guest)
    call(alice, "/api/register", "POST", {"username": "alice", "password": "alicepw"})
    _, me = call(alice, "/api/login", "POST", {"username": "alice", "password": "alicepw"})
    assert_eq(me["user"]["role"], "guest", "alice should start as guest")
    assert_eq(sorted(me["user"]["allowed_ops"]), ["+", "-"], "guest ops")

    # root login
    root = client()
    _, root_me = call(root, "/api/login", "POST", {"username": "root", "password": "root123"})
    assert_eq(root_me["user"]["role"], "superadmin")

    # Promote alice -> member
    _, users = call(root, "/api/users", "GET")
    alice_id = next(u["id"] for u in users["users"] if u["username"] == "alice")
    call(root, "/api/users/role", "POST", {"user_id": alice_id, "role": "member"})

    # alice re-login (old session got invalidated server-side)
    alice2 = client()
    _, me2 = call(alice2, "/api/login", "POST", {"username": "alice", "password": "alicepw"})
    assert_eq(me2["user"]["role"], "member", "alice should be member now")
    assert_eq(sorted(me2["user"]["allowed_ops"]), ["*", "+", "-", "/"], "member ops")
    print("  OK")

    # -------- Scenario B: ban blocks login --------
    print("Scenario B: ban prevents login")
    call(root, "/api/users/ban", "POST", {"user_id": alice_id, "banned": True})
    status, payload = call(client(), "/api/login", "POST",
                           {"username": "alice", "password": "alicepw"},
                           expect_ok=False)
    assert_eq(payload.get("ok"), False)
    if "封禁" not in payload.get("error", ""):
        raise AssertionError("ban message missing: " + str(payload))
    # Unban so later scenarios aren't affected
    call(root, "/api/users/ban", "POST", {"user_id": alice_id, "banned": False})
    print("  OK")

    # -------- Scenario C: math rule tampering --------
    print("Scenario C: tamper math rules")
    bob = client()
    call(bob, "/api/register", "POST", {"username": "bob", "password": "bobpw"})
    call(bob, "/api/login", "POST", {"username": "bob", "password": "bobpw"})
    _, r1 = call(bob, "/api/calc", "POST", {"a": "2", "op": "+", "b": "2"})
    assert_eq(r1["result"], "4", "normal 2+2")

    # root sets 2 + 2 = 5
    _, added = call(root, "/api/overrides", "POST",
                    {"a": "2", "op": "+", "b": "2", "result": "5"})
    key = added["key"]
    _, r2 = call(bob, "/api/calc", "POST", {"a": "2", "op": "+", "b": "2"})
    assert_eq(r2["result"], "5", "tampered 2+2")

    # delete rule, bob sees normal again
    call(root, "/api/overrides/delete", "POST", {"key": key})
    _, r3 = call(bob, "/api/calc", "POST", {"a": "2", "op": "+", "b": "2"})
    assert_eq(r3["result"], "4", "restored 2+2")
    print("  OK")

    # -------- Scenario D: permission bypass attempt --------
    print("Scenario D: server rejects unauthorized operator")
    # bob is guest. Try multiplication through the API directly.
    status, payload = call(bob, "/api/calc", "POST",
                           {"a": "3", "op": "*", "b": "4"}, expect_ok=False)
    assert_eq(payload.get("ok"), False)
    if status != 403:
        raise AssertionError(f"expected 403, got {status}")
    if "无权" not in payload.get("error", ""):
        raise AssertionError("forbidden message missing: " + str(payload))
    print("  OK")

    # -------- Extra: history records the tampered value --------
    print("Extra: history contains tampered result")
    # fresh tamper + calc + history check
    _, added = call(root, "/api/overrides", "POST",
                    {"a": "9", "op": "/", "b": "3", "result": "0"})
    call(bob, "/api/logout", "POST", {})
    # bob is guest and has no division, so do it as root
    call(root, "/api/calc", "POST", {"a": "9", "op": "/", "b": "3"})
    _, hist = call(root, "/api/history", "GET")
    latest = hist["history"][0]
    assert_eq(latest["result"], "0", "history should store tampered 0")
    call(root, "/api/overrides/delete", "POST", {"key": added["key"]})
    print("  OK")

    print("\nAll scenarios passed.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
    except Exception as e:
        print("ERROR:", repr(e))
        sys.exit(2)
