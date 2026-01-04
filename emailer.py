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


def send_services_lead_email(name: str, email: str, needs: str, user_id: int | None = None):
    """Send a services lead to the sales inbox."""
    lines = [
        "A new services request was submitted.",
        f"Name: {name}",
        f"Email: {email}",
    ]
    if user_id is not None:
        lines.append(f"User ID: {user_id}")
    lines.append("")
    lines.append("Needs / Requirements:")
    lines.append(needs)

    _send_email("RayGrow Services Request", "hradmin@raygrowcs.com", "\n".join(lines))


def send_services_ack_email(to_email: str, name: str, needs: str):
    """Send an acknowledgement back to the requester."""
    body = (
        f"Hi {name or 'there'},\n\n"
        "Thanks for reaching out to RayGrow about your services needs. "
        "We received your request and will follow up shortly.\n\n"
        "You shared the following:\n"
        f"{needs}\n\n"
        "If any of this changes, just reply to this email.\n\n"
        "— RayGrow Services Team"
    )
    _send_email("We received your services request", to_email, body)


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
