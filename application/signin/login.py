import argparse
import sys
import getpass
import importlib.util
from pathlib import Path
from datetime import datetime
import sqlite3
import hashlib
import secrets
import hmac

try:
    from data.database import init_db
    from data.dataloader import authenticate_user, set_current_user
except ImportError:
    import sys

    APP_ROOT = Path(__file__).resolve().parent.parent
    if str(APP_ROOT) not in sys.path:
        sys.path.append(str(APP_ROOT))
    from data.database import init_db
    from data.dataloader import authenticate_user, set_current_user


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    args = parser.parse_args()
    init_db()
    username = args.username or input("用户名: ")
    password = args.password or getpass.getpass("密码: ")
    ok = authenticate_user(username, password)
    if not ok:
        print("登录失败: 用户名或密码错误")
        sys.exit(1)
    set_current_user(username)
    print(f"登录成功: {username}")


if __name__ == "__main__":
    main()
