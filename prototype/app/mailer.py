import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger("camagru.mail")


def base_url():
    return os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")


def send(to, subject, body):
    msg = EmailMessage()
    msg["From"] = os.environ.get("MAIL_FROM", "camagru@localhost")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(os.environ.get("SMTP_HOST", "mailpit"),
                          int(os.environ.get("SMTP_PORT", "1025")), timeout=5) as smtp:
            smtp.send_message(msg)
        return True
    except OSError:
        log.error("could not send mail to a user")
        return False
