"""Authentication, session, and permission helpers.

Passwords are stored as SHA-256(salt + password) with a per-user random salt.
Sessions are opaque random tokens stored in SQLite and delivered via cookie.
"""
import hashlib
import secrets

import db


# Which operators each role may use. Checked on every /api/calc call.
ROLE_OPS = {
    "guest":      {"+", "-"},
    "member":     {"+", "-", "*", "/"},
    "admin":      {"+", "-", "*", "/"},
    "superadmin": {"+", "-", "*", "/"},
}

ROLE_RANK = {"guest": 0, "member": 1, "admin": 2, "superadmin": 3}


# ---------- Password hashing ----------

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return h, salt


def verify_password(password, pw_hash, pw_salt):
    h, _ = hash_password(password, pw_salt)
    # Constant-time compare
    return secrets.compare_digest(h, pw_hash)


# ---------- Session management ----------

def new_session_token():
    return secrets.token_urlsafe(32)


def login(username, password):
    """Return (user_dict, token) or raise ValueError with user-facing message."""
    user = db.get_user_by_username(username)
    if not user:
        raise ValueError("用户名或密码错误")
    if user["banned"]:
        raise ValueError("账号已被封禁")
    if not verify_password(password, user["pw_hash"], user["pw_salt"]):
        raise ValueError("用户名或密码错误")
    token = new_session_token()
    db.create_session(token, user["id"])
    return user, token


def register(username, password):
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        raise ValueError("用户名和密码不能为空")
    if len(username) > 32 or len(password) > 128:
        raise ValueError("用户名或密码过长")
    if db.get_user_by_username(username):
        raise ValueError("用户名已存在")
    pw_hash, pw_salt = hash_password(password)
    uid = db.create_user(username, pw_hash, pw_salt, role="guest")
    return db.get_user_by_id(uid)


def logout(token):
    if token:
        db.delete_session(token)


def current_user(token):
    if not token:
        return None
    sess = db.get_session(token)
    if not sess:
        return None
    user = db.get_user_by_id(sess["user_id"])
    if not user:
        return None
    # If the user got banned mid-session, kill the session.
    if user["banned"]:
        db.delete_session(token)
        return None
    return user


# ---------- Permission checks ----------

def can_use_op(role, op):
    return op in ROLE_OPS.get(role, set())


def allowed_ops(role):
    # Keep a stable order for the UI.
    order = ["+", "-", "*", "/"]
    ops = ROLE_OPS.get(role, set())
    return [o for o in order if o in ops]


def can_manage_users(role):
    return role in ("admin", "superadmin")


def can_tamper_rules(role):
    return role == "superadmin"


def can_change_target(actor_role, target_role):
    """Admin cannot touch other admins / superadmins. Superadmin can touch anyone except itself (handled at call-site)."""
    if actor_role == "superadmin":
        return True
    if actor_role == "admin":
        return target_role in ("guest", "member")
    return False
