"""Envoi d'emails transactionnels via SMTP.

Configuration (variables d'environnement) :
  SMTP_HOST, SMTP_PORT (587 ou 465), SMTP_USER, SMTP_PASSWORD, MAIL_FROM.
Si SMTP_HOST n'est pas configuré, on journalise simplement le contenu
(cas du développement / tests) et on renvoie False.
Si MAIL_DEBUG=true, les emails sont aussi affichés dans les logs.
"""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_email(to, subject, body_text):
    """Envoie un email. Renvoie True si envoyé, False sinon (SMTP non configuré ou erreur)."""
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        logger.info("[MAIL DEBUG] Aucun SMTP configuré — contenu de l'email :\nÀ: %s\nObjet: %s\n\n%s", to, subject, body_text)
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = (os.environ.get("MAIL_FROM", "") or user or "no-reply@localhost").strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body_text)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context()) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        logger.info("Email envoyé à %s (%s)", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec d'envoi de l'email à %s : %s", to, exc)
        return False