import smtplib
from email.mime.text import MIMEText
import logging

# --- Cấu hình ---
# Lấy trực tiếp từ file config/settings.py của bạn
# Hãy đảm bảo mật khẩu là "Mật khẩu ứng dụng" từ Google
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'khanh2003dakdoa@gmail.com'
EMAIL_HOST_PASSWORD = 'dgck nbii ribp wtly'  # QUAN TRỌNG: Dán "Mật khẩu ứng dụng" vào đây
EMAIL_USE_TLS = True
EMAIL_RECEIVER = 'superkklot2001@gmail.com'

# --- Cấu hình logging chi tiết ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_test_email():
    """Hàm gửi email test với debug output."""
    logger.info("Attempting to send a test email...")
    try:
        msg = MIMEText("This is a test email from the surveillance system script.")
        msg['Subject'] = "Test Email"
        msg['From'] = EMAIL_HOST_USER
        msg['To'] = EMAIL_RECEIVER

        # Bật debuglevel=1 để xem toàn bộ giao tiếp với server SMTP
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.set_debuglevel(1) 
        
        logger.info("Connecting to SMTP server...")
        server.starttls()
        logger.info("Logging in...")
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        logger.info("Sending email...")
        server.send_message(msg)
        server.quit()

        logger.info("Test email sent successfully!")
        
    except Exception as e:
        logger.error(f"Failed to send test email: {e}", exc_info=True)

if __name__ == '__main__':
    send_test_email() 