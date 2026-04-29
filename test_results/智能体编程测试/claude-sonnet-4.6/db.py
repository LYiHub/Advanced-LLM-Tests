"""
db.py - Database operations module
Uses SQLite3 (Python standard library only)
"""
import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "calc.db")


def get_connection():
    """Get a database connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    """Initialize database schema and seed superadmin account."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'guest'
                             CHECK(role IN ('guest','member','admin','superadmin')),
            banned   INTEGER NOT NULL DEFAULT 0,
            created_at TEXT  NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Sessions table (token-based auth)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Calculation history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calc_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expression TEXT    NOT NULL,
            result     TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Seed superadmin if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'root'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, 'superadmin')",
            ("root", hash_password("root123"))
        )

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# User operations
# ──────────────────────────────────────────────

def create_user(username: str, password: str) -> dict:
    """Register a new guest user. Returns user dict or raises ValueError."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, 'guest')",
            (username, hash_password(password))
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        raise ValueError(f"Username '{username}' already exists.")
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    """Fetch user record by username."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch user record by id."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_users() -> list[dict]:
    """Return all users (id, username, role, banned)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, username, role, banned FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_user_role(target_id: int, new_role: str):
    """Update a user's role."""
    valid_roles = ("guest", "member", "admin", "superadmin")
    if new_role not in valid_roles:
        raise ValueError(f"Invalid role: {new_role}")
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_id))
        conn.commit()
    finally:
        conn.close()


def set_user_banned(target_id: int, banned: bool):
    """Ban or unban a user."""
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET banned = ? WHERE id = ?", (1 if banned else 0, target_id))
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Session operations
# ──────────────────────────────────────────────

def create_session(user_id: int, token: str):
    """Persist a new session token."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO sessions (token, user_id) VALUES (?, ?)",
            (token, user_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_session(token: str) -> dict | None:
    """Return session record or None."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token: str):
    """Delete a session (logout)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Calculation history
# ──────────────────────────────────────────────

def add_history(user_id: int, expression: str, result: str):
    """Append a calculation record."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO calc_history (user_id, expression, result) VALUES (?, ?, ?)",
            (user_id, expression, result)
        )
        conn.commit()
    finally:
        conn.close()


def get_history(user_id: int, limit: int = 10) -> list[dict]:
    """Return the most recent N calculation records for a user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT expression, result, created_at FROM calc_history "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
