import smtplib
import configparser
import os
import platform
from email.message import EmailMessage
from pathlib import Path

# =========================
# LOAD host-specific app config
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
_raw_hostname = (
    os.environ.get("COMPUTERNAME")
    or os.environ.get("HOSTNAME")
    or platform.node()
    or "local"
)
_safe_hostname = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in _raw_hostname).strip("-_") or "local"
_host_ini = BASE_DIR / f"app-{_safe_hostname}.in"
_fallback_ini = BASE_DIR / "app.ini"
INI_PATH = _host_ini if _host_ini.exists() else _fallback_ini

cfg = configparser.ConfigParser()
cfg.read(INI_PATH)

if "email" not in cfg:
    raise RuntimeError(f"Missing [email] section in {INI_PATH.name}")

SMTP_HOST = cfg.get("email", "smtp_host")
SMTP_PORT = cfg.getint("email", "smtp_port", fallback=587)
SMTP_USER = cfg.get("email", "smtp_user")
SMTP_PASS = cfg.get("email", "smtp_pass")
FROM_EMAIL = cfg.get("email", "smtp_from", fallback=SMTP_USER)
FROM_NAME = cfg.get("email", "smtp_from_name", fallback="Mailer")

TO_EMAIL = "james@rcpro.in"

# =========================
# BUILD MESSAGE
# =========================
msg = EmailMessage()
msg["Subject"] = f"SMTP TEST (from {INI_PATH.name})"
msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
msg["To"] = TO_EMAIL
msg.set_content(f"Hello! This email was sent using SMTP settings from {INI_PATH.name}")

print("Connecting to SMTP server...")
print("Host:", SMTP_HOST)
print("Port:", SMTP_PORT)
print("User:", SMTP_USER)

# =========================
# SEND MAIL (TLS / 587)
# =========================
with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
    smtp.set_debuglevel(1)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()

    print("Logging in...")
    smtp.login(SMTP_USER, SMTP_PASS)

    print("Sending email...")
    smtp.send_message(msg)

print("✅ Email sent successfully")
