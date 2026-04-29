"""HTTP server entry point. Uses only Python standard library.

Run:
    python server.py
Then open http://localhost:8080
"""
import json
import os
import sys
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import auth
import calculator
import db


HOST = "0.0.0.0"
PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
COOKIE_NAME = "session"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _sanitize_user(u):
    """Drop password hash/salt before serializing."""
    if not u:
        return None
    return {
        "id": u["id"],
        "username": u["username"],
        "role": u["role"],
        "banned": bool(u["banned"]),
        "allowed_ops": auth.allowed_ops(u["role"]),
        "can_manage": auth.can_manage_users(u["role"]),
        "can_tamper": auth.can_tamper_rules(u["role"]),
    }


class APIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Handler(BaseHTTPRequestHandler):
    server_version = "CalcServer/1.0"

    # Silence the default per-request log spam, keep errors.
    def log_message(self, format, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    # ------------- low-level response helpers -------------

    def _send_json(self, status, payload, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status, message):
        self._send_json(status, {"ok": False, "error": message})

    def _send_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            self._send_error_json(HTTPStatus.NOT_FOUND, "Not found")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ------------- request parsing -------------

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > 1_000_000:
            raise APIError(HTTPStatus.BAD_REQUEST, "请求体过大")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            raise APIError(HTTPStatus.BAD_REQUEST, "JSON 解析失败")
        if not isinstance(data, dict):
            raise APIError(HTTPStatus.BAD_REQUEST, "请求体必须是 JSON 对象")
        return data

    def _get_cookie_token(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        c = SimpleCookie()
        try:
            c.load(raw)
        except Exception:
            return None
        m = c.get(COOKIE_NAME)
        return m.value if m else None

    def _require_user(self):
        token = self._get_cookie_token()
        user = auth.current_user(token)
        if not user:
            raise APIError(HTTPStatus.UNAUTHORIZED, "未登录")
        return user, token

    # ------------- dispatch -------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            # Static assets
            if method == "GET" and (path == "/" or path == "/index.html"):
                return self._send_file(os.path.join(STATIC_DIR, "index.html"),
                                       "text/html; charset=utf-8")
            if method == "GET" and path.startswith("/static/"):
                rel = path[len("/static/"):].replace("..", "")
                fpath = os.path.join(STATIC_DIR, rel)
                if not os.path.isfile(fpath):
                    return self._send_error_json(HTTPStatus.NOT_FOUND, "Not found")
                ext = os.path.splitext(fpath)[1].lower()
                ctype = {
                    ".html": "text/html; charset=utf-8",
                    ".css":  "text/css; charset=utf-8",
                    ".js":   "application/javascript; charset=utf-8",
                    ".json": "application/json; charset=utf-8",
                }.get(ext, "application/octet-stream")
                return self._send_file(fpath, ctype)

            # JSON API
            if path == "/api/register" and method == "POST":
                return self._api_register()
            if path == "/api/login" and method == "POST":
                return self._api_login()
            if path == "/api/logout" and method == "POST":
                return self._api_logout()
            if path == "/api/me" and method == "GET":
                return self._api_me()
            if path == "/api/calc" and method == "POST":
                return self._api_calc()
            if path == "/api/history" and method == "GET":
                return self._api_history()
            if path == "/api/users" and method == "GET":
                return self._api_users()
            if path == "/api/users/role" and method == "POST":
                return self._api_set_role()
            if path == "/api/users/ban" and method == "POST":
                return self._api_ban()
            if path == "/api/overrides" and method == "GET":
                return self._api_list_overrides()
            if path == "/api/overrides" and method == "POST":
                return self._api_set_override()
            if path == "/api/overrides/delete" and method == "POST":
                return self._api_delete_override()

            self._send_error_json(HTTPStatus.NOT_FOUND, "未知接口")
        except APIError as e:
            self._send_error_json(e.status, e.message)
        except Exception as e:  # last-resort safety net
            self.log_error("Unhandled: %r", e)
            self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "服务器内部错误")

    # ------------- auth endpoints -------------

    def _api_register(self):
        body = self._read_json_body()
        username = body.get("username")
        password = body.get("password")
        try:
            user = auth.register(username, password)
        except ValueError as e:
            raise APIError(HTTPStatus.BAD_REQUEST, str(e))
        self._send_json(HTTPStatus.OK, {"ok": True, "user": _sanitize_user(user)})

    def _api_login(self):
        body = self._read_json_body()
        username = body.get("username") or ""
        password = body.get("password") or ""
        try:
            user, token = auth.login(username, password)
        except ValueError as e:
            raise APIError(HTTPStatus.UNAUTHORIZED, str(e))
        cookie = SimpleCookie()
        cookie[COOKIE_NAME] = token
        cookie[COOKIE_NAME]["path"] = "/"
        cookie[COOKIE_NAME]["httponly"] = True
        cookie[COOKIE_NAME]["samesite"] = "Lax"
        hdr = [("Set-Cookie", cookie.output(header="").strip())]
        self._send_json(HTTPStatus.OK,
                        {"ok": True, "user": _sanitize_user(user)},
                        extra_headers=hdr)

    def _api_logout(self):
        token = self._get_cookie_token()
        auth.logout(token)
        cookie = SimpleCookie()
        cookie[COOKIE_NAME] = ""
        cookie[COOKIE_NAME]["path"] = "/"
        cookie[COOKIE_NAME]["max-age"] = 0
        hdr = [("Set-Cookie", cookie.output(header="").strip())]
        self._send_json(HTTPStatus.OK, {"ok": True}, extra_headers=hdr)

    def _api_me(self):
        token = self._get_cookie_token()
        user = auth.current_user(token)
        if not user:
            return self._send_json(HTTPStatus.OK, {"ok": True, "user": None})
        self._send_json(HTTPStatus.OK, {"ok": True, "user": _sanitize_user(user)})

    # ------------- calculator endpoints -------------

    def _api_calc(self):
        user, _ = self._require_user()
        body = self._read_json_body()
        a = body.get("a")
        op = body.get("op")
        b = body.get("b")
        if op not in ("+", "-", "*", "/"):
            raise APIError(HTTPStatus.BAD_REQUEST, "不支持的运算符")
        if not auth.can_use_op(user["role"], op):
            raise APIError(HTTPStatus.FORBIDDEN,
                           f"当前角色（{user['role']}）无权使用运算符 {op}")
        try:
            result = calculator.compute(a, op, b)
        except ValueError as e:
            raise APIError(HTTPStatus.BAD_REQUEST, str(e))
        formatted = calculator.format_result(result)
        expr = f"{calculator._normalize_num(calculator.parse_number(a))} {op} " \
               f"{calculator._normalize_num(calculator.parse_number(b))}"
        db.add_history(user["id"], expr, formatted)
        self._send_json(HTTPStatus.OK, {
            "ok": True,
            "expression": expr,
            "result": formatted,
        })

    def _api_history(self):
        user, _ = self._require_user()
        rows = db.recent_history(user["id"], 10)
        self._send_json(HTTPStatus.OK, {"ok": True, "history": rows})

    # ------------- admin endpoints -------------

    def _api_users(self):
        user, _ = self._require_user()
        if not auth.can_manage_users(user["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权访问用户列表")
        users = db.list_users()
        for u in users:
            u["banned"] = bool(u["banned"])
        self._send_json(HTTPStatus.OK, {"ok": True, "users": users})

    def _api_set_role(self):
        actor, _ = self._require_user()
        if not auth.can_manage_users(actor["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权管理用户")
        body = self._read_json_body()
        target_id = body.get("user_id")
        new_role = body.get("role")
        if new_role not in ("guest", "member", "admin", "superadmin"):
            raise APIError(HTTPStatus.BAD_REQUEST, "无效角色")
        target = db.get_user_by_id(target_id)
        if not target:
            raise APIError(HTTPStatus.NOT_FOUND, "目标用户不存在")
        if target["id"] == actor["id"]:
            raise APIError(HTTPStatus.BAD_REQUEST, "不能修改自己的角色")
        if not auth.can_change_target(actor["role"], target["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权修改该用户")
        # Admin can only assign guest/member (can't promote to admin+)
        if actor["role"] == "admin" and new_role not in ("guest", "member"):
            raise APIError(HTTPStatus.FORBIDDEN, "admin 只能设置 guest 或 member")
        # Nobody creates new superadmins via the UI
        if new_role == "superadmin":
            raise APIError(HTTPStatus.FORBIDDEN, "不能通过界面设置超级管理员")
        db.set_user_role(target["id"], new_role)
        # Invalidate their sessions so permissions refresh next login
        db.delete_sessions_for_user(target["id"])
        self._send_json(HTTPStatus.OK, {"ok": True})

    def _api_ban(self):
        actor, _ = self._require_user()
        if not auth.can_manage_users(actor["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权管理用户")
        body = self._read_json_body()
        target_id = body.get("user_id")
        banned = bool(body.get("banned"))
        target = db.get_user_by_id(target_id)
        if not target:
            raise APIError(HTTPStatus.NOT_FOUND, "目标用户不存在")
        if target["id"] == actor["id"]:
            raise APIError(HTTPStatus.BAD_REQUEST, "不能封禁自己")
        if not auth.can_change_target(actor["role"], target["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权修改该用户")
        db.set_user_banned(target["id"], banned)
        if banned:
            db.delete_sessions_for_user(target["id"])
        self._send_json(HTTPStatus.OK, {"ok": True})

    # ------------- rule override endpoints -------------

    def _api_list_overrides(self):
        user, _ = self._require_user()
        if not auth.can_tamper_rules(user["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权查看篡改规则")
        self._send_json(HTTPStatus.OK,
                        {"ok": True, "overrides": calculator.list_overrides()})

    def _api_set_override(self):
        user, _ = self._require_user()
        if not auth.can_tamper_rules(user["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权设置篡改规则")
        body = self._read_json_body()
        try:
            key = calculator.set_override(
                body.get("a"), body.get("op"), body.get("b"), body.get("result")
            )
        except ValueError as e:
            raise APIError(HTTPStatus.BAD_REQUEST, str(e))
        self._send_json(HTTPStatus.OK, {"ok": True, "key": key})

    def _api_delete_override(self):
        user, _ = self._require_user()
        if not auth.can_tamper_rules(user["role"]):
            raise APIError(HTTPStatus.FORBIDDEN, "无权删除篡改规则")
        body = self._read_json_body()
        key = body.get("key")
        if not key:
            raise APIError(HTTPStatus.BAD_REQUEST, "缺少 key")
        ok = calculator.delete_override(key)
        if not ok:
            raise APIError(HTTPStatus.NOT_FOUND, "规则不存在")
        self._send_json(HTTPStatus.OK, {"ok": True})


def main():
    db.init_db()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Calculator server running on http://localhost:{PORT}")
    print("Default superadmin: root / root123")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        srv.server_close()


if __name__ == "__main__":
    main()
