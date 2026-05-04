"""Notificari prin email SMTP.

Daca SMTP nu e configurat (smtp_host gol), alertele sunt scrise in data/alerts.log
si functia returneaza graceful (nu ridica exceptie).
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage

from app.config import DATA_DIR, settings

logger = logging.getLogger(__name__)
ALERTS_LOG = DATA_DIR / "alerts.log"


def _log_alert(destinatar: str, subiect: str, mesaj: str) -> None:
    line = (
        f"[{datetime.utcnow().isoformat()}] -> {destinatar}\n"
        f"  SUBJECT: {subiect}\n"
        f"  BODY: {mesaj.replace(chr(10), ' | ')}\n"
    )
    with ALERTS_LOG.open("a", encoding="utf-8") as f:
        f.write(line)
    logger.warning("ALERTA agro -> %s | %s", destinatar, subiect)


def send_alert(destinatar: str, subiect: str, mesaj: str) -> bool:
    """Trimite email cu alerta. Returneaza True daca SMTP a fost folosit, False -> log."""
    if not settings.smtp_host:
        _log_alert(destinatar, subiect, mesaj)
        return False

    try:
        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = destinatar
        msg["Subject"] = subiect
        msg.set_content(mesaj)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Alerta SMTP trimisa catre %s", destinatar)
        return True
    except Exception as exc:
        logger.exception("Eroare SMTP, scriu in alerts.log: %s", exc)
        _log_alert(destinatar, subiect, f"[SMTP_FAIL: {exc}]\n{mesaj}")
        return False
