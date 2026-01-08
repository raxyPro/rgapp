#
import os
import configparser
import platform
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
_raw_hostname = (
    os.environ.get("COMPUTERNAME")
    or os.environ.get("HOSTNAME")
    or platform.node()
    or "local"
)
_safe_hostname = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in _raw_hostname).strip("-_") or "local"
if "hosting.com" in _raw_hostname:
    _safe_hostname = "prod1"

_host_ini = BASE_DIR / f"app-{_safe_hostname}.ini"
_fallback_ini = BASE_DIR / "app.ini"

INI_PATH = _host_ini if _host_ini.exists() else _fallback_ini
print(_host_ini)
print(INI_PATH)

#exit(1)

config = configparser.ConfigParser()

if not INI_PATH.exists():
    raise RuntimeError(f"Configuration file not found: {INI_PATH}")

config.read(INI_PATH)


class Config:
    # --- App ---
    SECRET_KEY = config.get("app", "secret_key", fallback="dev-change-me")
    APP_BASE_URL = config.get("app", "app_base_url", fallback="http://localhost:5000")
    APP_SUBPATH = config.get("app", "app_subpath", fallback="")
    APP_ENFORCE_SUBPATH = config.getboolean("app", "app_enforce_subpath", fallback=False)
    REGISTER_BASE_URL = config.get("app", "register_base_url", fallback=APP_BASE_URL)
    DEV_LOGIN_ENABLED = config.getboolean("app", "dev_login", fallback=False)

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
        raise RuntimeError(f"SQLALCHEMY_DATABASE_URI is required in {INI_PATH.name}")

    # --- Email / SMTP ---
    SMTP_HOST = config.get("email", "smtp_host", fallback="")
    SMTP_PORT = config.getint("email", "smtp_port", fallback=587)
    SMTP_USER = config.get("email", "smtp_user", fallback="")
    SMTP_PASS = config.get("email", "smtp_pass", fallback="")
    SMTP_FROM = config.get("email", "smtp_from", fallback="no-reply@raygrowbridge.com")
    SMTP_FROM_NAME = config.get("email", "smtp_from_name", fallback="RayGrow Bridge")
    SMTP_USE_TLS = config.getboolean("email", "smtp_use_tls", fallback=True)
    SMTP_USE_SSL = config.getboolean("email", "smtp_use_ssl", fallback=False)
    SMTP_AUTH = config.getboolean("email", "smtp_auth", fallback=True)
    SMTP_TIMEOUT = config.getint("email", "smtp_timeout", fallback=30)
    SMTP_DEBUG = config.getboolean("email", "smtp_debug", fallback=False)

    # --- HTTP logging ---
    HTTP_LOG_ENABLED = config.getboolean("logging", "http_log_enabled", fallback=False)
    HTTP_LOG_PATH = config.get("logging", "http_log_path", fallback=str(BASE_DIR / "http.log"))
    HTTP_LOG_DIR = config.get("logging", "http_log_dir", fallback=str(BASE_DIR / "logs"))
    HTTP_LOG_BASENAME = config.get("logging", "http_log_basename", fallback="http.log")

    # --- Error logging ---
    ERROR_LOG_ENABLED = config.getboolean("logging", "error_log_enabled", fallback=True)
    ERROR_LOG_PATH = config.get("logging", "error_log_path", fallback=str(BASE_DIR / "error.log"))
    ERROR_LOG_DIR = config.get("logging", "error_log_dir", fallback=str(BASE_DIR / "logs"))
    ERROR_LOG_BASENAME = config.get("logging", "error_log_basename", fallback="error.log")
