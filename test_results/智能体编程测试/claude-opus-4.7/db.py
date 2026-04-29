"""SQLite data-access layer for the multi-role calculator.

Tables:
  users     - account records (id, username, pw_hash, pw_salt, role, banned)
  sessions  - session tokens (token, user_id, created_at)
  history   - per-user calculation history
Overrides (math-rule tampering) live in-memory only; see calculator.py.
"""
import os
import sqlite3
import threading
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calc.db")

# SQLite connections are not safe to share across threads without a lock.
# Using one connection + a lock keeps things simple for a standard-library server.
_lock = threading.Lock()
_conn = None


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conn():
    global _conn
    if _conn is None:
        _conn = _connect()
    return _conn


def init_db():
    """Create tables if missing; seed the superadmin account."""
    conn = get_conn()
    with _lock:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                pw_hash  TEXT NOT NULL,
                pw_salt  TEXT NOT NULL,
                role     TEXT NOT NULL CHECK(role IN ('guest','member','admin','superadmin')),
                banned   INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                expression TEXT NOT NULL,
                result     TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

    # Seed the superadmin if the users table is empty of superadmins.
    from auth import hash_password  # local import to avoid cycle at import time

    row = conn.execute(
        "SELECT id FROM users WHERE username = ?", ("root",)
    ).fetchone()
    if row is None:
        pw_hash, pw_salt = hash_password("root123")
        with _lock:
            conn.execute(
                "INSERT INTO users (username, pw_hash, pw_salt, role, banned, created_at) "
                "VALUES (?, ?, ?, 'superadmin', 0, ?)",
                ("root", pw_hash, pw_salt, int(time.time())),
            )


# ---------- User ops ----------

def create_user(username, pw_hash, pw_salt, role="guest"):
    conn = get_conn()
    with _lock:
        cur = conn.execute(
            "INSERT INTO users (username, pw_hash, pw_salt, role, banned, created_at) "
            "VALUES (?, ?, ?, ?, 0, ?)",
            (username, pw_hash, pw_salt, role, int(time.time())),
        )
        return cur.lastrowid


def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None


def list_users():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, username, role, banned, created_at FROM users ORDER BY id ASC"
    ).fetchall()
    return [dict(r) for r in rows]


def set_user_role(uid, role):
    if role not in ("guest", "member", "admin", "superadmin"):
        raise ValueError("invalid role")
    conn = get_conn()
    with _lock:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, uid))


def set_user_banned(uid, banned):
    conn = get_conn()
    with _lock:
        conn.execute(
            "UPDATE users SET banned = ? WHERE id = ?",
            (1 if banned else 0, uid),
        )


# ---------- Session ops ----------

def create_session(token, user_id):
    conn = get_conn()
    with _lock:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, int(time.time())),
        )


def get_session(token):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    return dict(row) if row else None


def delete_session(token):
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_sessions_for_user(user_id):
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


# ---------- History ops ----------

def add_history(user_id, expression, result):
    conn = get_conn()
    with _lock:
        conn.execute(
            "INSERT INTO history (user_id, expression, result, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, expression, str(result), int(time.time())),
        )


def recent_history(user_id, limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT expression, result, created_at FROM history "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
