import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger("email_service")

class EmailService:
    @staticmethod
    def send_due_date_reminder(
        to_email: str,
        member_name: str,
        order_id: str,
        book_titles: List[str],
        due_date: str
    ) -> bool:
        """
        Sends a due date reminder email to a library member.
        Falls back to logging if SMTP settings are not fully configured.
        """
        subject = f"Library Reminder: Books Due on {due_date} (Order {order_id})"
        books_formatted = "\n".join([f"  • {title}" for title in book_titles])

        body_text = (
            f"Dear {member_name},\n\n"
            f"This is a friendly reminder from the Library Management System that the following book(s) "
            f"borrowed under Order #{order_id} are due on {due_date}:\n\n"
            f"{books_formatted}\n\n"
            f"Please ensure they are returned on or before the due date.\n\n"
            f"Thank you,\n"
            f"Library Team"
        )

        if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
            logger.info(f"[MOCK EMAIL SENT] To: {to_email} | Subject: {subject}\nBody:\n{body_text}")
            return True

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())
            server.quit()
            logger.info(f"Successfully sent due date reminder email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
