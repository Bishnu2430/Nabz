"""Outgoing email. In development every message lands in the Mailpit inbox (http://localhost:8025)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("nabz.mail")
outbox: list[EmailMessage] = []  # the "memory" backend, for tests


def send(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if settings.mail_backend == "memory":
        outbox.append(msg)
        return
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.send_message(msg)
    except OSError as exc:  # a mail outage must not break sign-up; the user can ask for the email again
        log.warning("email to a user could not be sent: %s", type(exc).__name__)


TEXT = {
    "verify": {
        "en": ("Confirm your email for Nabz",
               "Welcome to Nabz.\n\nConfirm your email address to start uploading reports:\n{link}\n\n"
               "This link works once and expires in 24 hours. If you didn't sign up, ignore this email."),
        "hi": ("नब्ज़ के लिए अपना ईमेल पक्का करें",
               "नब्ज़ में आपका स्वागत है।\n\nरिपोर्ट अपलोड करने के लिए अपना ईमेल पक्का करें:\n{link}\n\n"
               "यह लिंक एक बार चलता है और 24 घंटे में समाप्त हो जाता है। अगर आपने साइन अप नहीं किया, तो इसे अनदेखा करें।"),
    },
    "reset": {
        "en": ("Reset your Nabz password",
               "Someone asked to reset the password for this email on Nabz.\n\nChoose a new password here:\n{link}\n\n"
               "This link works once and expires in 30 minutes. If it wasn't you, ignore this email; your password "
               "hasn't changed."),
        "hi": ("नब्ज़ का पासवर्ड बदलें",
               "किसी ने नब्ज़ पर इस ईमेल का पासवर्ड बदलने को कहा है।\n\nनया पासवर्ड यहाँ चुनें:\n{link}\n\n"
               "यह लिंक एक बार चलता है और 30 मिनट में समाप्त हो जाता है। अगर यह आप नहीं थे, तो इसे अनदेखा करें।"),
    },
    "exists": {
        "en": ("Someone tried to sign up with your email",
               "Someone tried to create a Nabz account with this email, which already has one.\n\n"
               "If it was you, sign in instead, or reset your password:\n{link}"),
    },
}


def send_template(kind: str, to: str, language: str, link: str) -> None:
    texts = TEXT[kind]
    subject, body = texts.get(language) or texts["en"]
    send(to, subject, body.format(link=link))
