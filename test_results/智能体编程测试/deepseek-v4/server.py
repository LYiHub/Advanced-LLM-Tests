"""
HTTP server for the multi-role calculator.
Uses only Python standard library: http.server + json + sqlite3.
"""

import json
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import db
import auth
import calculator

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def json_response(handler, data, status=200):
    """Send a JSON response."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def json_error(handler, message, status=400):
    """Send a JSON error response."""
    json_response(handler, {"error": message}, status)


def read_json_body(handler):
    """Read and parse JSON request body."""
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        if content_length == 0:
            return None
        body = handler.rfile.read(content_length)
        return json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return None


def get_current_user(handler):
    """Get authenticated user from cookie. Returns (user, error_response_tuple)."""
    user = auth.get_user_from_request(handler.headers)
    if user is None:
        return None, ("Not authenticated", 401)
    if user.get("banned"):
        # Invalidate token on ban
        db.set_user_token(user["id"], None)
        return None, ("Account has been banned", 403)
    return user, None


def require_role(handler, roles):
    """Check if current user has one of the required roles. Returns (user, error_tuple)."""
    user, err = get_current_user(handler)
    if err:
        return None, err
    if user["role"] not in roles:
        return None, ("Insufficient permissions", 403)
    return user, None


# ── Route table ──

def handle_api(handler, method, path, query, body):
    """Route API requests to handlers. Returns (data, status) tuple."""

    # ── Auth routes ──
    if method == "POST" and path == "/api/register":
        return handle_register(body)
    if method == "POST" and path == "/api/login":
        return handle_login(body, handler)
    if method == "POST" and path == "/api/logout":
        return handle_logout(handler)

    # ── Self ──
    if method == "GET" and path == "/api/me":
        return handle_me(handler)

    # ── Calculate ──
    if method == "POST" and path == "/api/calculate":
        return handle_calculate(handler, body)

    # ── History ──
    if method == "GET" and path == "/api/history":
        return handle_history(handler)
    if method == "DELETE" and path == "/api/history":
        return handle_clear_history(handler)

    # ── Admin: user management ──
    if method == "GET" and path == "/api/users":
        return handle_list_users(handler)
    if method == "POST" and path == "/api/users/role":
        return handle_change_role(handler, body)
    if method == "POST" and path == "/api/users/ban":
        return handle_ban_user(handler, body)
    if method == "POST" and path == "/api/users/unban":
        return handle_unban_user(handler, body)

    # ── Superadmin: tamper rules ──
    if method == "GET" and path == "/api/rules":
        return handle_list_rules(handler)
    if method == "POST" and path == "/api/rules":
        return handle_add_rule(handler, body)
    if method == "DELETE" and re.match(r"^/api/rules/(\d+)$", path):
        match = re.match(r"^/api/rules/(\d+)$", path)
        return handle_delete_rule(handler, int(match.group(1)))

    return {"error": "Not found"}, 404


# ── Auth handlers ──

def handle_register(body):
    if not body:
        return {"error": "Missing request body"}, 400
    username = body.get("username", "").strip()
    password = body.get("password", "")
    user, err = auth.register(username, password)
    if err:
        return {"error": err}, 400
    return {"id": user["id"], "username": user["username"], "role": user["role"]}, 201


def handle_login(body, handler):
    if not body:
        return {"error": "Missing request body"}, 400
    username = body.get("username", "").strip()
    password = body.get("password", "")
    user, err = auth.login(username, password)
    if err:
        return {"error": err}, 401
    # Set cookie
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Set-Cookie", f"token={user['token']}; Path=/; HttpOnly; SameSite=Lax")
    resp_body = json.dumps({"id": user["id"], "username": user["username"], "role": user["role"]},
                           ensure_ascii=False).encode("utf-8")
    handler.send_header("Content-Length", str(len(resp_body)))
    handler.end_headers()
    handler.wfile.write(resp_body)
    return None, None  # Special: handler already sent response


def handle_logout(handler):
    user, _ = get_current_user(handler)
    # get_current_user returns tuple of (user, error), and user might be None
    # we need to handle this differently
    token = None
    cookie_header = handler.headers.get("Cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("token="):
            token = part[6:]
            break
    if token:
        user_obj = db.get_user_by_token(token)
        if user_obj:
            db.set_user_token(user_obj["id"], None)

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Set-Cookie", "token=; Path=/; HttpOnly; Max-Age=0; SameSite=Lax")
    resp_body = b'{"ok":true}'
    handler.send_header("Content-Length", str(len(resp_body)))
    handler.end_headers()
    handler.wfile.write(resp_body)
    return None, None


def handle_me(handler):
    user, err = get_current_user(handler)
    if err:
        return {"error": err[0]}, err[1]
    return {"id": user["id"], "username": user["username"], "role": user["role"]}, 200


# ── Calculate handler ──

def handle_calculate(handler, body):
    user, err = get_current_user(handler)
    if err:
        return {"error": err[0]}, err[1]
    if not body:
        return {"error": "Missing request body"}, 400
    a = body.get("a")
    op = body.get("op")
    b = body.get("b")
    if a is None or op is None or b is None:
        return {"error": "Missing a, op, or b"}, 400

    # Permission check: does this user's role allow this operation?
    role_perms = auth.ROLE_PERMISSIONS.get(user["role"], {})
    allowed_ops = role_perms.get("ops", set())
    # Normalize operator
    std_op = {"+": "+", "-": "-", "×": "*", "÷": "/", "*": "*", "/": "/"}.get(str(op).strip(), str(op).strip())
    if std_op not in allowed_ops:
        return {"error": f"Operation '{op}' is not allowed for role '{user['role']}'"}, 403

    result, tampered, calc_err = calculator.calculate(a, op, b)
    if calc_err:
        return {"error": calc_err}, 400

    # Build display expression
    op_display = calculator.OP_SYMBOLS.get(std_op, std_op)
    a_num, _, b_num, _ = calculator.normalize_expression(a, op, b)
    a_str = _fmt_num(a_num)
    b_str = _fmt_num(b_num)
    r_str = _fmt_num(result)
    expression = f"{a_str} {op_display} {b_str}"

    # Save to history
    db.add_history(user["id"], expression, result, tampered)

    return {
        "expression": expression,
        "result": result,
        "tampered": tampered,
    }, 200


# ── History handler ──

def handle_history(handler):
    user, err = get_current_user(handler)
    if err:
        return {"error": err[0]}, err[1]
    records = db.get_history(user["id"])
    return {"history": records}, 200

def handle_clear_history(handler):
    user, err = get_current_user(handler)
    if err:
        return {"error": err[0]}, err[1]
    db.clear_history(user["id"])
    return {"ok": True}, 200


# ── Admin: list users ──

def handle_list_users(handler):
    user, err = require_role(handler, ["admin", "superadmin"])
    if err:
        return {"error": err[0]}, err[1]
    users = db.get_all_users()
    return {"users": users}, 200


# ── Admin: change role ──

def handle_change_role(handler, body):
    actor, err = require_role(handler, ["admin", "superadmin"])
    if err:
        return {"error": err[0]}, err[1]
    if not body:
        return {"error": "Missing request body"}, 400
    user_id = body.get("user_id")
    new_role = body.get("role")
    if user_id is None or not new_role:
        return {"error": "Missing user_id or role"}, 400
    if new_role not in ("guest", "member", "admin"):
        return {"error": f"Invalid role: {new_role}"}, 400

    target = db.get_user_by_id(user_id)
    if target is None:
        return {"error": "User not found"}, 404

    if actor["role"] == "admin" and target["role"] in ("admin", "superadmin"):
        return {"error": "Cannot modify admin or superadmin"}, 403

    if not auth.can_manage_role(actor["role"], target["role"], new_role):
        return {"error": "Cannot change this user's role"}, 403

    db.update_user_role(user_id, new_role)
    return {"ok": True, "user_id": user_id, "role": new_role}, 200


# ── Admin: ban / unban ──

def handle_ban_user(handler, body):
    actor, err = require_role(handler, ["admin", "superadmin"])
    if err:
        return {"error": err[0]}, err[1]
    if not body:
        return {"error": "Missing request body"}, 400
    user_id = body.get("user_id")
    if user_id is None:
        return {"error": "Missing user_id"}, 400

    target = db.get_user_by_id(user_id)
    if target is None:
        return {"error": "User not found"}, 404

    if not auth.can_ban_user(actor["role"], target["role"]):
        return {"error": "Cannot ban this user"}, 403

    # Invalidate token on ban
    db.set_user_token(user_id, None)
    db.set_user_banned(user_id, 1)
    return {"ok": True, "user_id": user_id, "banned": True}, 200


def handle_unban_user(handler, body):
    actor, err = require_role(handler, ["admin", "superadmin"])
    if err:
        return {"error": err[0]}, err[1]
    if not body:
        return {"error": "Missing request body"}, 400
    user_id = body.get("user_id")
    if user_id is None:
        return {"error": "Missing user_id"}, 400

    target = db.get_user_by_id(user_id)
    if target is None:
        return {"error": "User not found"}, 404

    if not auth.can_ban_user(actor["role"], target["role"]):
        return {"error": "Cannot unban this user"}, 403

    db.set_user_banned(user_id, 0)
    return {"ok": True, "user_id": user_id, "banned": False}, 200


# ── Superadmin: tamper rules ──

def handle_list_rules(handler):
    user, err = require_role(handler, ["superadmin"])
    if err:
        return {"error": err[0]}, err[1]
    rules = calculator.get_tamper_rules()
    return {"rules": [calculator.format_rule(r) for r in rules]}, 200


def handle_add_rule(handler, body):
    user, err = require_role(handler, ["superadmin"])
    if err:
        return {"error": err[0]}, err[1]
    if not body:
        return {"error": "Missing request body"}, 400
    a = body.get("a")
    op = body.get("op")
    b = body.get("b")
    result_val = body.get("result")
    if a is None or op is None or b is None or result_val is None:
        return {"error": "Missing a, op, b, or result"}, 400

    rule, rule_err = calculator.add_tamper_rule(a, op, b, result_val)
    if rule_err:
        return {"error": rule_err}, 400

    return {"rule": calculator.format_rule(rule)}, 201


def handle_delete_rule(handler, rule_id):
    user, err = require_role(handler, ["superadmin"])
    if err:
        return {"error": err[0]}, err[1]
    if calculator.remove_tamper_rule(rule_id):
        return {"ok": True, "deleted": rule_id}, 200
    return {"error": "Rule not found"}, 404


# ── Utility ──

def _fmt_num(n):
    """Format a number nicely."""
    if isinstance(n, float) and n == int(n) and n != float("inf"):
        return str(int(n))
    return str(n)


# ── Static file serving ──

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def serve_static(handler, path):
    """Serve a static file from the static/ directory."""
    if path == "/":
        path = "/index.html"

    # Security: prevent directory traversal
    safe_path = os.path.normpath(path.lstrip("/"))
    full_path = os.path.join(STATIC_DIR, safe_path)

    if not full_path.startswith(os.path.abspath(STATIC_DIR)):
        handler.send_error(403)
        return

    if not os.path.isfile(full_path):
        handler.send_error(404)
        return

    ext = os.path.splitext(full_path)[1].lower()
    mime = MIME_TYPES.get(ext, "application/octet-stream")

    try:
        with open(full_path, "rb") as f:
            content = f.read()
        handler.send_response(200)
        handler.send_header("Content-Type", mime)
        handler.send_header("Content-Length", str(len(content)))
        handler.end_headers()
        handler.wfile.write(content)
    except IOError:
        handler.send_error(500)


# ── Request Handler ──

class CalculatorHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler."""

    def log_message(self, format, *args):
        """Override to print cleaner logs."""
        print(f"[{self.command}] {args[0]}")

    def handle_request(self):
        """Central request dispatcher."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        body = read_json_body(self)

        # API routes
        if path.startswith("/api/"):
            data, status = handle_api(self, self.command, path, query, body)
            if data is not None:
                json_response(self, data, status)
            # If data is None, the handler already sent the response (e.g., login with cookie)
            return

        # Static files
        serve_static(self, path)

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()


# ── Main ──

def main():
    print("Initializing database...")
    db.init_db()
    print(f"Database ready at {db.DB_PATH}")

    print(f"Starting server on http://localhost:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), CalculatorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
