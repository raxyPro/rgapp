import os
import configparser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INI_PATH = BASE_DIR / "app.ini"

config = configparser.ConfigParser()

if not INI_PATH.exists():
    raise RuntimeError(f"Configuration file not found: {INI_PATH}")

config.read(INI_PATH)


class Config:
    # --- App ---
    SECRET_KEY = config.get("app", "secret_key", fallback="dev-change-me")
    APP_BASE_URL = config.get("app", "app_base_url", fallback="http://localhost:5000")

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = config.get(
        "database",
        "sqlalchemy_database_uri",
        fallback=None
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Keep connections fresh to avoid stale sockets on reload/idle timeouts
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_timeout": 30,
        "pool_size": 5,
        "max_overflow": 10,
    }

    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is required in app.ini")

    # --- Email / SMTP ---
    SMTP_HOST = config.get("email", "smtp_host", fallback="")
    SMTP_PORT = config.getint("email", "smtp_port", fallback=587)
    SMTP_USER = config.get("email", "smtp_user", fallback="")
    SMTP_PASS = config.get("email", "smtp_pass", fallback="")
    SMTP_FROM = config.get("email", "smtp_from", fallback="no-reply@raygrowbridge.com")
    SMTP_FROM_NAME = config.get("email", "smtp_from_name", fallback="RayGrow Bridge")

