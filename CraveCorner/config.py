"""Local configuration loading with safe, uncommitted development secrets."""

from __future__ import annotations

import os
import secrets
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = PROJECT_DIR / "instance"


def _load_dotenv() -> None:
    env_file = PROJECT_DIR / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("\"'")
        if name and name not in os.environ:
            os.environ[name] = value


def _secret_key() -> str:
    key = os.getenv("SESSION_SECRET") or os.getenv("FLASK_SECRET_KEY")
    if key:
        return key

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    key_file = INSTANCE_DIR / "local_secret_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()

    key = secrets.token_urlsafe(48)
    key_file.write_text(key, encoding="utf-8")
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    return key


def load_config() -> dict[str, object]:
    _load_dotenv()
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "SECRET_KEY": _secret_key(),
        "DATABASE": os.getenv(
            "CRAVECORNER_DB", str(INSTANCE_DIR / "cravecorner.sqlite3")
        ),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.getenv("COOKIE_SECURE", "false").lower()
        in {"true", "1", "yes"},
        "PERMANENT_SESSION_LIFETIME": 60 * 60 * 8,
        "MAX_CONTENT_LENGTH": 64 * 1024,
    }
