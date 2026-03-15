import sqlite3
from data.database import get_connection
from data.security import hash_password, verify_password
from data.dataloader import get_user_by_username


def change_password(username: str, old_password: str, new_password: str) -> bool:

    if not username or not old_password or not new_password:
        return False

    row = get_user_by_username(username)
    if row is None:
        return False

    stored_pwd = row[1]
    try:
        pwd_hash, salt_hex, iters = stored_pwd.split("$")
        if not verify_password(old_password, salt_hex, int(iters), pwd_hash):
            return False

        new_pwd_hash, new_salt_hex, new_iters = hash_password(new_password)
        new_stored_pwd = f"{new_pwd_hash}${new_salt_hex}${new_iters}"

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE users SET password=? WHERE username=?",
                (new_stored_pwd, username),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error during password change: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    except ValueError:
        return False
