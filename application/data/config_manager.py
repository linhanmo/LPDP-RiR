import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_CONFIG = {"language": "CN"}


def load_config():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")


def get_language():
    config = load_config()
    return config.get("language", "CN")


def set_language(lang):
    config = load_config()
    config["language"] = lang
    save_config(config)


def save_credentials(username, password, remember_me):
    config = load_config()
    if remember_me:
        config["remember_me"] = True
        config["saved_username"] = username
        config["saved_password"] = password
    else:
        config["remember_me"] = False
        config.pop("saved_username", None)
        config.pop("saved_password", None)
    save_config(config)


def get_credentials():
    config = load_config()
    if config.get("remember_me", False):
        return config.get("saved_username", ""), config.get("saved_password", "")
    return "", ""


def get_remember_me_status():
    config = load_config()
    return config.get("remember_me", False)


def get_theme_index():
    config = load_config()
    return config.get("theme_index", 1)


def set_theme_index(index):
    config = load_config()
    config["theme_index"] = index
    save_config(config)
