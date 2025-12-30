import smtplib
import configparser
from email.message import EmailMessage
from pathlib import Path

# =========================
# LOAD app.ini
# =========================
BASE_DIR = Path(__file__).resolve().parent
INI_PATH = BASE_DIR / "app.ini"

cfg = configparser.ConfigParser()
cfg.read(INI_PATH)

if "email" not in cfg:
    raise RuntimeError("Missing [email] section in app.ini")

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
msg["Subject"] = "SMTP TEST (from app.ini)"
msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
msg["To"] = TO_EMAIL
msg.set_content("Hello! This email was sent using SMTP settings from app.ini")

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
