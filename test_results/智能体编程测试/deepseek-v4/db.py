"""
Database module for multi-role calculator.
Uses SQLite3 for persistence.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calc.db")


def get_conn():
    """Get a database connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database tables and superadmin account."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'guest',
            banned INTEGER NOT NULL DEFAULT 0,
            token TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            expression TEXT NOT NULL,
            result REAL NOT NULL,
            tampered INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Create superadmin if not exists
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    root_hash = salt + ":" + hashlib.sha256((salt + "root123").encode()).hexdigest()
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, role, banned, token)
        VALUES ('root', ?, 'superadmin', 0, NULL)
    """, (root_hash,))

    conn.commit()
    conn.close()


# ── User operations ──

def create_user(username, password_hash):
    """Create a new user with guest role. Returns user dict or None if username taken."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, banned) VALUES (?, ?, 'guest', 0)",
            (username, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Get user by ID."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username):
    """Get user by username."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_token(token):
    """Get user by session token."""
    if not token:
        return None
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def set_user_token(user_id, token):
    """Set or clear a user's session token."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET token = ? WHERE id = ?", (token, user_id))
    conn.commit()
    conn.close()


def get_all_users():
    """Get all users (for admin panel)."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, banned FROM users ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_role(user_id, role):
    """Update a user's role."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()


def set_user_banned(user_id, banned):
    """Set a user's banned status (1 = banned, 0 = active)."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = ? WHERE id = ?", (banned, user_id))
    conn.commit()
    conn.close()


# ── History operations ──

def add_history(user_id, expression, result, tampered=False):
    """Add a calculation record. Keeps only the last 10 per user."""
    from datetime import datetime
    conn = get_conn()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO history (user_id, expression, result, tampered, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, expression, result, 1 if tampered else 0, now)
    )
    # Prune to last 10
    cursor.execute("""
        DELETE FROM history WHERE id NOT IN (
            SELECT id FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 10
        ) AND user_id = ?
    """, (user_id, user_id))
    conn.commit()
    conn.close()


def get_history(user_id, limit=10):
    """Get recent calculation history for a user."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT expression, result, tampered, created_at FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_history(user_id):
    """Clear all calculation history for a user."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
