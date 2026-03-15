import sqlite3
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data.db"
SESSION_FILE = APP_DIR / ".session_user"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            registration_time TEXT,
            last_log_in_time TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datastorage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            foldername TEXT,
            FOREIGN KEY(username) REFERENCES users(username)
        )
        """
    )
    conn.commit()
    conn.close()
