import smtplib
from email.mime.text import MIMEText
from config import settings
import logging

logger = logging.getLogger(__name__)

def send_email_alert(subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = settings.EMAIL_RECEIVER

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)

        logger.info("Email alert sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
