import json
import os

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SilaStali")
FILE = os.path.join(APP_DIR, "session.json")


def _load():
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    os.makedirs(APP_DIR, exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_session():
    return _load()


def has_session():
    return bool(_load().get("token"))


def save_login(token, user_id, username, full_name, role, block=None):
    d = _load()
    d.pop("pin_hash", None)
    d.update({
        "token": token,
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "role": role,
        "block": block,
    })
    _save(d)


def clear():
    try:
        os.remove(FILE)
    except FileNotFoundError:
        pass


def set_username(username):
    d = _load()
    d["username"] = username
    _save(d)