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
    from data.dataloader import create_user, set_current_user
except ImportError:
    import sys

    APP_ROOT = Path(__file__).resolve().parent.parent
    if str(APP_ROOT) not in sys.path:
        sys.path.append(str(APP_ROOT))
    from data.database import init_db
    from data.dataloader import create_user, set_current_user


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    parser.add_argument("--autologin", action="store_true")
    args = parser.parse_args()
    init_db()
    username = args.username or input("设置用户名: ")
    password = args.password or getpass.getpass("设置密码: ")
    confirm = getpass.getpass("确认密码: ") if args.password is None else password
    if password != confirm:
        print("注册失败: 两次输入的密码不一致")
        sys.exit(1)
    ok = create_user(username, password)
    if not ok:
        print("注册失败: 用户名已存在或非法输入")
        sys.exit(1)
    print(f"注册成功: {username}")
    if args.autologin:
        set_current_user(username)
        print(f"已自动登录: {username}")


if __name__ == "__main__":
    main()
