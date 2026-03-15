import sqlite3
from pathlib import Path
from datetime import datetime
from .database import get_connection, init_db, SESSION_FILE
from .security import hash_password, verify_password


def get_current_user():
    if not SESSION_FILE.exists():
        return None
    try:
        return SESSION_FILE.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def delete_user_data(username: str) -> bool:
    if not username:
        return False

    conn = get_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("DELETE FROM datastorage WHERE username=?", (username,))
        cursor = conn.execute("DELETE FROM users WHERE username=?", (username,))

        if cursor.rowcount == 0:
            conn.rollback()
            return False

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Database error during user deletion: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user_history(username: str):
    if not username:
        return []

    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT foldername FROM datastorage WHERE username=? ORDER BY id DESC",
            (username,),
        )
        return [row[0] for row in cur.fetchall()]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def get_user_by_username(username: str):
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT username, password FROM users WHERE username=?", (username,)
        )
        row = cur.fetchone()
        return row
    finally:
        conn.close()


def create_user(username: str, password: str):
    init_db()
    if not username or not password:
        return False
    if get_user_by_username(username) is not None:
        return False
    pwd_hash, salt_hex, iters = hash_password(password)
    stored_pwd = f"{pwd_hash}${salt_hex}${iters}"
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users(username, password, registration_time, last_log_in_time) VALUES(?,?,?,?)",
            (username, stored_pwd, datetime.now().isoformat(timespec="seconds"), None),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def authenticate_user(username: str, password: str):
    init_db()
    row = get_user_by_username(username)
    if row is None:
        return False
    stored_pwd = row[1]
    try:
        pwd_hash, salt_hex, iters = stored_pwd.split("$")
        if verify_password(password, salt_hex, int(iters), pwd_hash):
            conn = get_connection()
            try:
                conn.execute(
                    "UPDATE users SET last_log_in_time=? WHERE username=?",
                    (datetime.now().isoformat(timespec="seconds"), username),
                )
                conn.commit()
            finally:
                conn.close()
            return True
        return False
    except ValueError:
        return False


def set_current_user(username: str):
    SESSION_FILE.write_text(username, encoding="utf-8")


def verify_data_integrity():
    from .database import APP_DIR

    root_dir = APP_DIR.parent
    input_root = root_dir / "input"
    output_root = root_dir / "output"

    conn = get_connection()
    try:
        cursor = conn.execute("SELECT id, foldername FROM datastorage")
        records = cursor.fetchall()

        ids_to_delete = []

        for record_id, foldername in records:
            out_path = output_root / foldername
            in_path = input_root / foldername

            if not out_path.exists():
                ids_to_delete.append(record_id)

        if ids_to_delete:
            print(f"Cleaning up {len(ids_to_delete)} invalid records...")
            conn.executemany(
                "DELETE FROM datastorage WHERE id=?", [(rid,) for rid in ids_to_delete]
            )
            conn.commit()
            print("Cleanup complete.")

    except sqlite3.Error as e:
        print(f"Database error during integrity check: {e}")
    finally:
        conn.close()
