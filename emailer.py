import smtplib
from email.message import EmailMessage
from flask import current_app


def send_invite_email(to_email: str, invite_url: str):
    msg = EmailMessage()
    msg["Subject"] = "RayGrow Bridge Invitation"
    msg["From"] = f"{current_app.config['SMTP_FROM_NAME']} <{current_app.config['SMTP_FROM']}>"

    msg["To"] = to_email

    msg.set_content(
        f"You are invited to RayGrow Bridge.\n\n"
        f"Complete registration here:\n{invite_url}\n\n"
        f"If you did not expect this, ignore this email."
    )

    host = current_app.config["SMTP_HOST"]
    port = current_app.config["SMTP_PORT"]
    user = current_app.config["SMTP_USER"]
    pw = current_app.config["SMTP_PASS"]

    if not host:
        print("[DEV EMAIL] To:", to_email)
        print("[DEV EMAIL] INVITE URL:", invite_url)
        return

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        if user:
            smtp.login(user, pw)
        smtp.send_message(msg)


def send_reset_email(to_email: str, reset_url: str):
    msg = EmailMessage()
    msg["Subject"] = "RayGrow Bridge Password Reset"
    msg["From"] = f"{current_app.config['SMTP_FROM_NAME']} <{current_app.config['SMTP_FROM']}>"

    msg["To"] = to_email

    msg.set_content(
        f"Password reset requested.\n\n"
        f"Reset your password here:\n{reset_url}\n\n"
        f"If you did not request this, ignore this email."
    )

    host = current_app.config["SMTP_HOST"]
    port = current_app.config["SMTP_PORT"]
    user = current_app.config["SMTP_USER"]
    pw = current_app.config["SMTP_PASS"]

    if not host:
        print("[DEV EMAIL] To:", to_email)
        print("[DEV EMAIL] RESET URL:", reset_url)
        return

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        if user:
            smtp.login(user, pw)
        smtp.send_message(msg)
