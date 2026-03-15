import sqlite3
from pathlib import Path
import sys

try:
    from .database import get_connection
except ImportError:
    APP_DIR = Path(__file__).resolve().parent.parent.parent
    if str(APP_DIR / "application") not in sys.path:
        sys.path.append(str(APP_DIR / "application"))
    from data.database import get_connection


def cleanup_invalid_records():
    print("Running database cleanup...")
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT id, foldername FROM datastorage")
        records = cursor.fetchall()

        current_dir = Path(__file__).resolve().parent
        app_dir = current_dir.parent
        input_dir = app_dir / "input"
        output_dir = app_dir / "output"

        deleted_count = 0

        for record_id, foldername in records:
            if not foldername:
                continue

            input_path = input_dir / foldername
            output_path = output_dir / foldername

            if not input_path.exists():
                print(
                    f"Record {record_id} ({foldername}) invalid: Input folder missing. Deleting..."
                )
                conn.execute("DELETE FROM datastorage WHERE id=?", (record_id,))
                deleted_count += 1
        if deleted_count > 0:
            conn.commit()
            print(f"Cleanup complete. Deleted {deleted_count} invalid records.")
        else:
            print("Cleanup complete. No invalid records found.")

    except sqlite3.Error as e:
        print(f"Database error during cleanup: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    cleanup_invalid_records()
