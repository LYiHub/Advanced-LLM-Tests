"""
server.py - HTTP server entry point (Python standard library only).
Run:  python server.py
Then open http://localhost:8080
"""
import json
import os
import sys
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs

import db
import auth
import calculator

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def json_response(handler, status: int, data: dict):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler, status: int, message: str):
    json_response(handler, status, {"ok": False, "error": message})


def ok_response(handler, data: dict = None):
    payload = {"ok": True}
    if data:
        payload.update(data)
    json_response(handler, 200, payload)


def read_body(handler) -> dict:
    """Read and parse JSON request body."""
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def get_token(handler) -> str | None:
    """Extract session token from Cookie header."""
    cookie_header = handler.headers.get("Cookie", "")
    if not cookie_header:
        return None
    sc = SimpleCookie()
    sc.load(cookie_header)
    morsel = sc.get("token")
    return morsel.value if morsel else None


def require_auth(handler) -> dict | None:
    """
    Resolve request user. Sends 401 and returns None if not authenticated.
    """
    token = get_token(handler)
    user = auth.get_current_user(token)
    if user is None:
        error_response(handler, 401, "未登录，请先登录")
        return None
    return user


def require_role(handler, user: dict, *roles) -> bool:
    """
    Check user role. Sends 403 and returns False if insufficient.
    """
    if user["role"] not in roles:
        error_response(handler, 403, "权限不足")
        return False
    return True


# ──────────────────────────────────────────────
# Request handler
# ──────────────────────────────────────────────

class CalcHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Suppress default request log noise; only print errors
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API routes
        if path == "/api/me":
            self._handle_me()
        elif path == "/api/history":
            self._handle_history()
        elif path == "/api/users":
            self._handle_list_users()
        elif path == "/api/rules":
            self._handle_list_rules()
        else:
            # Serve static files
            self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/register":
            self._handle_register()
        elif path == "/api/login":
            self._handle_login()
        elif path == "/api/logout":
            self._handle_logout()
        elif path == "/api/calculate":
            self._handle_calculate()
        elif path == "/api/admin/role":
            self._handle_set_role()
        elif path == "/api/admin/ban":
            self._handle_set_ban()
        elif path == "/api/rules":
            self._handle_set_rule()
        elif path == "/api/rules/delete":
            self._handle_delete_rule()
        else:
            error_response(self, 404, "接口不存在")

    # ── Static file serving ──────────────────

    def _serve_static(self, path: str):
        if path == "/" or path == "":
            path = "/index.html"
        # Sanitize path traversal
        rel = path.lstrip("/").replace("..", "")
        full_path = os.path.join(STATIC_DIR, rel)
        if not os.path.isfile(full_path):
            # Fallback: serve index.html for SPA-style navigation
            full_path = os.path.join(STATIC_DIR, "index.html")
        if not os.path.isfile(full_path):
            self.send_response(404)
            self.end_headers()
            return
        mime, _ = mimetypes.guess_type(full_path)
        mime = mime or "application/octet-stream"
        with open(full_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ── Auth endpoints ───────────────────────

    def _handle_register(self):
        body = read_body(self)
        username = body.get("username", "").strip()
        password = body.get("password", "")
        try:
            auth.register(username, password)
            ok_response(self, {"message": "注册成功"})
        except ValueError as e:
            error_response(self, 400, str(e))

    def _handle_login(self):
        body = read_body(self)
        username = body.get("username", "")
        password = body.get("password", "")
        try:
            result = auth.login(username, password)
            token = result["token"]
            # Set httpOnly cookie
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header(
                "Set-Cookie",
                f"token={token}; HttpOnly; Path=/; SameSite=Strict"
            )
            payload = json.dumps({"ok": True, "user": result["user"]}, ensure_ascii=False).encode("utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except ValueError as e:
            error_response(self, 401, str(e))

    def _handle_logout(self):
        token = get_token(self)
        if token:
            auth.logout(token)
        # Clear cookie
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header(
            "Set-Cookie",
            "token=; HttpOnly; Path=/; Max-Age=0; SameSite=Strict"
        )
        payload = json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_me(self):
        token = get_token(self)
        user = auth.get_current_user(token)
        if user is None:
            ok_response(self, {"user": None})
            return
        ok_response(self, {
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
            }
        })

    # ── Calculator endpoint ──────────────────

    def _handle_calculate(self):
        user = require_auth(self)
        if user is None:
            return

        body = read_body(self)
        operation = body.get("operation", "")
        try:
            a = float(body.get("a", 0))
            b_raw = body.get("b", None)
            b = float(b_raw) if b_raw is not None else None
        except (TypeError, ValueError):
            error_response(self, 400, "无效的数字参数")
            return

        # Permission check
        if not auth.can_operate(user["role"], operation):
            error_response(self, 403, f"您的角色（{user['role']}）无权执行该运算")
            return

        try:
            result = calculator.calculate(operation, a, b)
            expression = calculator.format_expression(operation, a, b)
            db.add_history(user["id"], f"{expression} = {result}", result)
            ok_response(self, {"result": result, "expression": expression})
        except ValueError as e:
            error_response(self, 400, str(e))

    def _handle_history(self):
        user = require_auth(self)
        if user is None:
            return
        records = db.get_history(user["id"], limit=10)
        ok_response(self, {"history": records})

    # ── Admin endpoints ──────────────────────

    def _handle_list_users(self):
        user = require_auth(self)
        if user is None:
            return
        if not require_role(self, user, "admin", "superadmin"):
            return
        users = db.list_users()
        ok_response(self, {"users": users})

    def _handle_set_role(self):
        actor = require_auth(self)
        if actor is None:
            return
        if not require_role(self, actor, "admin", "superadmin"):
            return

        body = read_body(self)
        try:
            target_id = int(body.get("target_id", 0))
            new_role = body.get("role", "")
            auth.admin_set_role(actor, target_id, new_role)
            ok_response(self, {"message": "角色已更新"})
        except (ValueError, PermissionError) as e:
            error_response(self, 400, str(e))

    def _handle_set_ban(self):
        actor = require_auth(self)
        if actor is None:
            return
        if not require_role(self, actor, "admin", "superadmin"):
            return

        body = read_body(self)
        try:
            target_id = int(body.get("target_id", 0))
            banned = bool(body.get("banned", True))
            auth.admin_set_banned(actor, target_id, banned)
            action = "封禁" if banned else "解封"
            ok_response(self, {"message": f"用户已{action}"})
        except (ValueError, PermissionError) as e:
            error_response(self, 400, str(e))

    # ── Rule tamper endpoints ────────────────

    def _handle_list_rules(self):
        user = require_auth(self)
        if user is None:
            return
        if not require_role(self, user, "superadmin"):
            return
        rules = calculator.list_rules()
        ok_response(self, {"rules": rules})

    def _handle_set_rule(self):
        user = require_auth(self)
        if user is None:
            return
        if not require_role(self, user, "superadmin"):
            return

        body = read_body(self)
        try:
            a = float(body.get("a", 0))
            operation = body.get("operation", "")
            b_raw = body.get("b", None)
            b = float(b_raw) if b_raw is not None else None
            result_str = str(body.get("result", "")).strip()

            if not result_str:
                raise ValueError("篡改结果不能为空")
            if operation not in calculator.SUPPORTED_OPS:
                raise ValueError(f"不支持的运算: {operation}")

            calculator.set_rule(a, operation, b, result_str)
            ok_response(self, {"message": "规则已设置"})
        except (ValueError, TypeError) as e:
            error_response(self, 400, str(e))

    def _handle_delete_rule(self):
        user = require_auth(self)
        if user is None:
            return
        if not require_role(self, user, "superadmin"):
            return

        body = read_body(self)
        try:
            a = float(body.get("a", 0))
            operation = body.get("operation", "")
            b_raw = body.get("b", None)
            b = float(b_raw) if b_raw is not None else None
            removed = calculator.delete_rule(a, operation, b)
            if removed:
                ok_response(self, {"message": "规则已删除"})
            else:
                error_response(self, 404, "规则不存在")
        except (ValueError, TypeError) as e:
            error_response(self, 400, str(e))


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    db.init_db()
    server = HTTPServer(("0.0.0.0", PORT), CalcHandler)
    print(f"✓ 数据库已初始化（calc.db）")
    print(f"✓ 服务器已启动：http://localhost:{PORT}")
    print(f"  默认超管账号：root / root123")
    print("  按 Ctrl+C 停止服务器")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止。")
        sys.exit(0)


if __name__ == "__main__":
    main()
