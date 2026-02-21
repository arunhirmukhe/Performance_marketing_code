"""Alert Service - sends notifications via Email and Slack."""

import logging
import httpx
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Sends alerts via email (SMTP) and Slack webhook."""

    async def send_alert(
        self, title: str, message: str, level: str = "info"
    ):
        """Send alert via all configured channels."""
        full_message = f"**{title}**\n\n{message}\n\nLevel: {level}"
        logger.info(f"Alert [{level}]: {title}")

        # Send via Slack
        if settings.SLACK_WEBHOOK_URL:
            try:
                await self._send_slack(title, message, level)
            except Exception as e:
                logger.error(f"Slack alert failed: {e}")

        # Send via Email
        if settings.SMTP_HOST and settings.ALERT_TO_EMAILS:
            try:
                await self._send_email(title, message, level)
            except Exception as e:
                logger.error(f"Email alert failed: {e}")

    async def _send_slack(self, title: str, message: str, level: str):
        """Send alert to Slack via webhook."""
        emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level, "📢")
        color = {"info": "#36a64f", "warning": "#ff9900", "critical": "#ff0000"}.get(level, "#cccccc")

        payload = {
            "attachments": [{
                "color": color,
                "title": f"{emoji} {title}",
                "text": message,
                "footer": "FAGE Automation Engine",
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
            response.raise_for_status()

    async def _send_email(self, title: str, message: str, level: str):
        """Send alert email via SMTP."""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            recipients = [e.strip() for e in settings.ALERT_TO_EMAILS.split(",") if e.strip()]
            if not recipients:
                return

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[FAGE {level.upper()}] {title}"
            msg["From"] = settings.ALERT_FROM_EMAIL
            msg["To"] = ", ".join(recipients)

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: {'#ff0000' if level == 'critical' else '#333'};">{title}</h2>
                <p>{message}</p>
                <hr>
                <p style="color: #888; font-size: 12px;">
                    FAGE Automation Engine | {level.upper()} Alert
                </p>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=True,
            )

        except ImportError:
            logger.warning("aiosmtplib not installed, skipping email alert")
