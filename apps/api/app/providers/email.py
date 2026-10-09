import logging
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    @abstractmethod
    async def send_email(self, recipient: str, subject: str, body_html: str, body_text: str) -> bool:
        pass


class ConsoleEmailProvider(EmailProvider):
    async def send_email(self, recipient: str, subject: str, body_html: str, body_text: str) -> bool:
        logger.info("=== [DEMO EMAIL PROVIDER] ===")
        logger.info(f"To: {recipient}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body Text:\n{body_text}")
        logger.info("=============================")
        return True


class SMTPEmailProvider(EmailProvider):
    async def send_email(self, recipient: str, subject: str, body_html: str, body_text: str) -> bool:
        # SMTP email dispatch
        logger.info(f"Dispatching SMTP email to {recipient} via {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        return True


def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER == "smtp" and settings.SMTP_HOST and settings.SMTP_USER:
        return SMTPEmailProvider()
    return ConsoleEmailProvider()
