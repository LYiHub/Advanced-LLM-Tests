"""
Authentication and permission logic.
- Password hashing with hashlib (sha256 + salt)
- Token-based session management (secrets.token_hex)
- Role-based permission checks
"""

import hashlib
import os
import secrets

import db


def hash_password(password):
    """Hash a password with a random salt using sha256. Returns 'salt:hash'."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password, stored):
    """Verify a password against a stored 'salt:hash' string."""
    try:
        salt, h = stored.split(":", 1)
        return h == hashlib.sha256((salt + password).encode()).hexdigest()
    except (ValueError, AttributeError):
        return False


def generate_token():
    """Generate a random session token."""
    return secrets.token_hex(32)


# ── Permission definitions ──

ROLE_PERMISSIONS = {
    "guest":      {"ops": {"+", "-"},                       "can_manage": False, "can_tamper": False},
    "member":     {"ops": {"+", "-", "*", "/"},             "can_manage": False, "can_tamper": False},
    "admin":      {"ops": {"+", "-", "*", "/"},             "can_manage": True,  "can_tamper": False},
    "superadmin": {"ops": {"+", "-", "*", "/"},             "can_manage": True,  "can_tamper": True},
}

ALLOWED_DOWNGRADE_TARGETS = {
    "superadmin": ["guest", "member", "admin"],     # can't downgrade superadmins
    "admin":      ["guest", "member"],               # can't touch admin or superadmin
    "member":     [],
    "guest":      [],
}


def can_manage_role(actor_role, target_role, new_role):
    """Check if actor can change target's role to new_role."""
    if actor_role == "superadmin":
        return True  # superadmin can do anything
    if actor_role != "admin":
        return False
    # admin cannot modify other admin or superadmin
    if target_role in ("admin", "superadmin"):
        return False
    return new_role in ALLOWED_DOWNGRADE_TARGETS.get("admin", [])


def can_ban_user(actor_role, target_role):
    """Check if actor can ban/unban target."""
    if actor_role == "superadmin":
        return True
    if actor_role == "admin" and target_role in ("guest", "member"):
        return True
    return False


def get_user_from_request(headers):
    """Extract user from Cookie header. Returns user dict or None."""
    cookie_header = headers.get("Cookie", "")
    token = None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("token="):
            token = part[6:]
            break
    if not token:
        return None
    return db.get_user_by_token(token)


# ── Auth actions ──

def register(username, password):
    """Register a new user. Returns (user_dict, error_message)."""
    if not username or not password:
        return None, "Username and password are required"
    if len(username) < 2 or len(username) > 32:
        return None, "Username must be 2-32 characters"
    if len(password) < 3 or len(password) > 64:
        return None, "Password must be 3-64 characters"

    password_hash = hash_password(password)
    user = db.create_user(username, password_hash)
    if user is None:
        return None, "Username already exists"
    return user, None


def login(username, password):
    """Authenticate a user. Returns (user_dict, error_message)."""
    if not username or not password:
        return None, "Username and password are required"

    user = db.get_user_by_username(username)
    if user is None:
        return None, "Invalid username or password"
    if user["banned"]:
        return None, "Account has been banned"

    if not verify_password(password, user["password_hash"]):
        return None, "Invalid username or password"

    # Generate and store token
    token = generate_token()
    db.set_user_token(user["id"], token)
    user["token"] = token
    return user, None


def logout(token):
    """Log out by clearing the token."""
    if token:
        user = db.get_user_by_token(token)
        if user:
            db.set_user_token(user["id"], None)
