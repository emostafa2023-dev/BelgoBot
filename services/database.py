import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "bot.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            group_number TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            is_done INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reminder_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            hours_before INTEGER DEFAULT 24,
            enabled INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher TEXT NOT NULL,
            text TEXT NOT NULL,
            rating INTEGER,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            points REAL,
            max_points REAL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)


# ---------- USERS ----------

def get_or_create_user(telegram_id: int) -> sqlite3.Row:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        if row:
            return row
        conn.execute(
            "INSERT INTO users (telegram_id, created_at) VALUES (?, ?)",
            (telegram_id, datetime.now().isoformat())
        )
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def set_user_group(telegram_id: int, group_number: str):
    get_or_create_user(telegram_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET group_number = ? WHERE telegram_id = ?",
            (group_number, telegram_id)
        )


def get_user_group(telegram_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT group_number FROM users WHERE telegram_id = ?",
            (telegram_id,)
        ).fetchone()
        return row["group_number"] if row else None


# ---------- DEADLINES ----------

def add_deadline(telegram_id: int, title: str, due_date: str,
                  description: str = "", source: str = "manual"):
    user = get_or_create_user(telegram_id)
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO deadlines (user_id, title, description, due_date, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user["id"], title, description, due_date, source, datetime.now().isoformat())
        )


def get_deadlines(telegram_id: int, only_active: bool = True):
    user = get_or_create_user(telegram_id)
    query = "SELECT * FROM deadlines WHERE user_id = ?"
    if only_active:
        query += " AND is_done = 0"
    query += " ORDER BY due_date ASC"
    with get_connection() as conn:
        return conn.execute(query, (user["id"],)).fetchall()


def mark_deadline_done(deadline_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE deadlines SET is_done = 1 WHERE id = ?", (deadline_id,))


def delete_deadline(deadline_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM deadlines WHERE id = ?", (deadline_id,))


# ---------- REMINDER SETTINGS ----------

def get_reminder_settings(telegram_id: int) -> sqlite3.Row:
    user = get_or_create_user(telegram_id)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reminder_settings WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if row:
            return row
        conn.execute(
            "INSERT INTO reminder_settings (user_id) VALUES (?)", (user["id"],)
        )
        return conn.execute(
            "SELECT * FROM reminder_settings WHERE user_id = ?", (user["id"],)
        ).fetchone()


def set_reminder_hours(telegram_id: int, hours_before: int):
    user = get_or_create_user(telegram_id)
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO reminder_settings (user_id, hours_before)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET hours_before = excluded.hours_before""",
            (user["id"], hours_before)
        )


def toggle_reminders(telegram_id: int) -> int:
    settings = get_reminder_settings(telegram_id)
    new_value = 0 if settings["enabled"] else 1
    with get_connection() as conn:
        conn.execute(
            "UPDATE reminder_settings SET enabled = ? WHERE user_id = ?",
            (new_value, settings["user_id"])
        )
    return new_value


# ---------- REVIEWS ----------

def add_review(teacher: str, text: str, rating=None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO reviews (teacher, text, rating, created_at) VALUES (?, ?, ?, ?)",
            (teacher, text, rating, datetime.now().isoformat())
        )


def get_reviews(teacher: str = None):
    with get_connection() as conn:
        if teacher:
            return conn.execute(
                "SELECT * FROM reviews WHERE teacher = ? ORDER BY created_at DESC",
                (teacher,)
            ).fetchall()
        return conn.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()