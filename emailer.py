import smtplib
from email.message import EmailMessage
from flask import current_app


def send_invite_email(to_email: str, invite_url: str):
    body = (
        "You are invited to RayGrow Bridge.\n\n"
        f"Complete registration here:\n{invite_url}\n\n"
        "If you did not expect this, ignore this email."
    )
    _send_email("RayGrow Bridge Invitation", to_email, body)


def send_reset_email(to_email: str, reset_url: str):
    body = (
        "Password reset requested.\n\n"
        f"Reset your password here:\n{reset_url}\n\n"
        "If you did not request this, ignore this email."
    )
    _send_email("RayGrow Bridge Password Reset", to_email, body)


def _send_email(subject: str, to_email: str, body: str):
    """Send an email using SMTP settings from Flask config (app.ini)."""
    cfg = current_app.config

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{cfg['SMTP_FROM_NAME']} <{cfg['SMTP_FROM']}>"
    msg["To"] = to_email
    msg.set_content(body)

    host = cfg.get("SMTP_HOST")
    port = cfg.get("SMTP_PORT")
    user = cfg.get("SMTP_USER")
    pw = cfg.get("SMTP_PASS")

    use_tls = cfg.get("SMTP_USE_TLS", True)
    use_ssl = cfg.get("SMTP_USE_SSL", False)
    use_auth = cfg.get("SMTP_AUTH", True)
    timeout = cfg.get("SMTP_TIMEOUT", 30)
    debug = cfg.get("SMTP_DEBUG", False)

    if not host:
        print("[DEV EMAIL] To:", to_email)
        print("[DEV EMAIL] Subject:", subject)
        print("[DEV EMAIL] Body:\n", body)
        return

    print("Connecting to SMTP server...")
    print("Host:", host)
    print("Port:", port)
    print("User:", user)

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(host, port, timeout=timeout) as smtp:
        smtp.set_debuglevel(1 if debug else 0)
        smtp.ehlo()
        if use_tls and not use_ssl:
            smtp.starttls()
            smtp.ehlo()

        if use_auth and user:
            print("Logging in...")
            smtp.login(user, pw)

        print("Sending email...")
        smtp.send_message(msg)
