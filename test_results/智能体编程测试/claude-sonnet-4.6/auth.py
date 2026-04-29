"""
auth.py - Authentication and permission logic
"""
import secrets
import db

# Role hierarchy (higher index = more privileges)
ROLE_HIERARCHY = ["guest", "member", "admin", "superadmin"]

# Operations each role is allowed to perform
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "guest":      {"add", "subtract"},
    "member":     {"add", "subtract", "multiply", "divide"},
    "admin":      {"add", "subtract", "multiply", "divide"},
    "superadmin": {"add", "subtract", "multiply", "divide", "power", "sqrt"},
}


def role_rank(role: str) -> int:
    """Return numeric rank of a role (higher = more privileged)."""
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return -1


def can_operate(role: str, operation: str) -> bool:
    """Check whether a role is allowed to perform an operation."""
    return operation in ROLE_PERMISSIONS.get(role, set())


def login(username: str, password: str) -> dict:
    """
    Authenticate user. Returns a dict with token and user info.
    Raises ValueError on bad credentials or banned account.
    """
    user = db.get_user_by_username(username)
    if user is None:
        raise ValueError("用户名或密码错误")

    if user["password"] != db.hash_password(password):
        raise ValueError("用户名或密码错误")

    if user["banned"]:
        raise ValueError("账号已被封禁")

    token = secrets.token_hex(32)
    db.create_session(user["id"], token)
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        }
    }


def logout(token: str):
    """Invalidate a session token."""
    db.delete_session(token)


def get_current_user(token: str) -> dict | None:
    """
    Resolve a session token to a user dict.
    Returns None if the token is invalid or the account is banned.
    """
    if not token:
        return None
    session = db.get_session(token)
    if session is None:
        return None
    user = db.get_user_by_id(session["user_id"])
    if user is None or user["banned"]:
        return None
    return user


def register(username: str, password: str) -> dict:
    """
    Register a new guest user.
    Raises ValueError if username already taken or inputs invalid.
    """
    username = username.strip()
    if not username:
        raise ValueError("用户名不能为空")
    if len(username) > 32:
        raise ValueError("用户名最长 32 个字符")
    if not password or len(password) < 4:
        raise ValueError("密码至少 4 个字符")

    return db.create_user(username, password)


def admin_set_role(actor: dict, target_id: int, new_role: str):
    """
    Admin/superadmin changes target user's role.
    Raises PermissionError on policy violations.
    """
    actor_role = actor["role"]
    if actor_role not in ("admin", "superadmin"):
        raise PermissionError("权限不足")

    target = db.get_user_by_id(target_id)
    if target is None:
        raise ValueError("目标用户不存在")

    # Cannot modify self
    if target["id"] == actor["id"]:
        raise PermissionError("不能修改自己的角色")

    # admin cannot touch other admin or superadmin
    if actor_role == "admin" and role_rank(target["role"]) >= role_rank("admin"):
        raise PermissionError("admin 无法修改同级或更高权限的用户")

    # superadmin can set any role; admin only guest/member
    if actor_role == "admin" and new_role not in ("guest", "member"):
        raise PermissionError("admin 只能将用户设为 guest 或 member")

    db.update_user_role(target_id, new_role)


def admin_set_banned(actor: dict, target_id: int, banned: bool):
    """
    Admin/superadmin bans or unbans a target user.
    """
    actor_role = actor["role"]
    if actor_role not in ("admin", "superadmin"):
        raise PermissionError("权限不足")

    target = db.get_user_by_id(target_id)
    if target is None:
        raise ValueError("目标用户不存在")

    if target["id"] == actor["id"]:
        raise PermissionError("不能封禁自己")

    # admin cannot touch admin or superadmin
    if actor_role == "admin" and role_rank(target["role"]) >= role_rank("admin"):
        raise PermissionError("admin 无法操作同级或更高权限的用户")

    db.set_user_banned(target_id, banned)
