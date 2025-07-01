import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from config import settings
import logging

logger = logging.getLogger(__name__)

def send_email_alert(subject, body, image_path=None):
    """
    Gửi email cảnh báo với tùy chọn đính kèm ảnh.
    
    Args:
        subject (str): Tiêu đề email
        body (str): Nội dung email
        image_path (str, optional): Đường dẫn đến file ảnh cần đính kèm
    """
    try:
        # Tạo message container
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = settings.EMAIL_RECEIVER

        # Thêm nội dung text
        msg.attach(MIMEText(body, 'plain'))

        # Đính kèm ảnh nếu có
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                
                # Tạo MIMEImage object
                image = MIMEImage(img_data)
                image.add_header('Content-Disposition', 
                               f'attachment; filename="{os.path.basename(image_path)}"')
                msg.attach(image)
                logger.info(f"Image attached: {image_path}")
            except Exception as e:
                logger.error(f"Failed to attach image {image_path}: {e}")
        elif image_path:
            logger.warning(f"Image file not found: {image_path}")

        # Gửi email
        logger.info("Connecting to SMTP server...")
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            logger.info("Connected to SMTP server")
            if settings.EMAIL_USE_TLS:
                logger.info("Starting TLS...")
                server.starttls()
                logger.info("TLS started")
            logger.info("Logging in...")
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            logger.info("Logged in, sending message...")
            server.send_message(msg)
            logger.info("Message sent to server")

        logger.info("Email alert sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
