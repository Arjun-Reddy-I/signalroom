import asyncio
import logging
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    @abstractmethod
    async def send_email(self, recipient: str, subject: str, body_html: str, body_text: str) -> bool:
        pass


class ConsoleEmailProvider(EmailProvider):
    """Logs emails to the console. Used when no SMTP is configured."""

    async def send_email(self, recipient: str, subject: str, body_html: str, body_text: str) -> bool:
        logger.info("=== [DEMO EMAIL — not sent] ===")
        logger.info(f"To: {recipient}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body:\n{body_text}")
        logger.info("================================")
        return True


class SMTPEmailProvider(EmailProvider):
    """Sends real email via SMTP using TLS (port 587) or SSL (port 465)."""

    def _build_message(self, recipient: str, subject: str, body_html: str, body_text: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = recipient
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        return msg

    def _send_sync(self, recipient: str, subject: str, body_html: str, body_text: str) -> bool:
        msg = self._build_message(recipient, subject, body_html, body_text)
        try:
            context = ssl.create_default_context()
            if settings.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.EMAILS_FROM_EMAIL, recipient, msg.as_string())
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.EMAILS_FROM_EMAIL, recipient, msg.as_string())
            logger.info(f"Email sent to {recipient}: {subject}")
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error(f"SMTP authentication failed for {settings.SMTP_USER}. Check SMTP_USER and SMTP_PASSWORD.")
            return False
        except smtplib.SMTPException as exc:
            logger.error(f"SMTP error sending to {recipient}: {exc}")
            return False
        except OSError as exc:
            logger.error(f"Network error connecting to SMTP {settings.SMTP_HOST}:{settings.SMTP_PORT}: {exc}")
            return False

    async def send_email(self, recipient: str, subject: str, body_html: str, body_text: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_sync, recipient, subject, body_html, body_text)


def get_email_provider() -> EmailProvider:
    if (
        settings.EMAIL_PROVIDER == "smtp"
        and settings.SMTP_HOST
        and settings.SMTP_USER
        and settings.SMTP_PASSWORD
    ):
        return SMTPEmailProvider()
    return ConsoleEmailProvider()
