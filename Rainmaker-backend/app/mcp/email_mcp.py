import os
import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

class EmailMCP:
    """A tool for sending and receiving emails via SMTP and IMAP."""

    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER or "smtp.gmail.com"
        self.smtp_port = 587
        self.imap_server = settings.IMAP_SERVER or "imap.gmail.com"
        self.email_address = settings.EMAIL_ADDRESS
        self.email_password = settings.EMAIL_PASSWORD.get_secret_value() if settings.EMAIL_PASSWORD else None

        if not all([self.email_address, self.email_password]):
            logger.warning("Email credentials (EMAIL_ADDRESS, EMAIL_PASSWORD) are not set. EmailMCP will not function.")

    def send_email(self, to: str, subject: str, body: str, thread_id: str = None) -> Dict[str, Any]:
        """Sends an email using SMTP with optional thread tracking."""
        if not all([self.email_address, self.email_password]):
            error_msg = "Email credentials are not configured."
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        msg = MIMEMultipart()
        msg['From'] = self.email_address
        msg['To'] = to
        msg['Subject'] = subject
        
        # Add thread tracking headers if provided
        if thread_id:
            msg['X-Thread-ID'] = thread_id
            # Generate a unique message ID
            import uuid
            message_id = f"<{uuid.uuid4()}@{self.email_address.split('@')[1]}>"
            msg['Message-ID'] = message_id
            
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
                logger.info(f"Email sent successfully to {to}")
                
                result = {"status": "success", "message": f"Email sent to {to}"}
                if thread_id:
                    result["thread_id"] = thread_id
                    result["message_id"] = message_id
                    
                return result
        except Exception as e:
            logger.error(f"Failed to send email to {to}", error=str(e))
            return {"status": "error", "message": str(e)}

    def check_for_replies(self, prospect_email: str, since_date: str = None) -> List[Dict[str, Any]]:
        """Checks for unread replies from a specific email address."""
        logger.info(f"Checking for replies from {prospect_email}")
        
        if not all([self.email_address, self.email_password]):
            logger.error("Email credentials are not configured.")
            return []

        replies = []
        try:
            logger.info(f"Connecting to IMAP server {self.imap_server}")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.email_password)
            mail.select("inbox")
            logger.info("Successfully connected to inbox")

            # Search for emails from the specific prospect with date filtering
            from datetime import datetime, timedelta
            if since_date:
                search_criteria = f'(FROM "{prospect_email}" SINCE {since_date})'
            else:
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
                search_criteria = f'(FROM "{prospect_email}" SINCE {yesterday})'
            logger.info(f"Searching with criteria: {search_criteria}")
            status, messages = mail.search(None, search_criteria)
            logger.info(f"Search status: {status}, messages: {messages}")
            
            if status != "OK":
                logger.error("Failed to search inbox.")
                mail.logout()
                return []

            message_nums = messages[0].split() if messages[0] else []
            logger.info(f"Found {len(message_nums)} emails from {prospect_email}")

            for num in message_nums:
                status, data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(data[0][1])
                
                # Basic check to ensure it's a reply or contains our thread indicators
                subject = msg["subject"] or ""
                from_addr = msg["from"] or ""
                
                # Check if it's a reply or from our prospect
                if "Re:" in subject or prospect_email.lower() in from_addr.lower():
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            cdispo = str(part.get('Content-Disposition'))

                            # Get the plain text part, ignore attachments
                            if ctype == 'text/plain' and 'attachment' not in cdispo:
                                try:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        # Try UTF-8 first, fall back to other encodings
                                        try:
                                            body = payload.decode('utf-8')
                                        except UnicodeDecodeError:
                                            try:
                                                body = payload.decode('latin-1')
                                            except UnicodeDecodeError:
                                                body = payload.decode('utf-8', errors='ignore')
                                        break
                                except Exception as e:
                                    logger.warning(f"Failed to decode email part: {e}")
                                    continue
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                # Try UTF-8 first, fall back to other encodings
                                try:
                                    body = payload.decode('utf-8')
                                except UnicodeDecodeError:
                                    try:
                                        body = payload.decode('latin-1')
                                    except UnicodeDecodeError:
                                        body = payload.decode('utf-8', errors='ignore')
                        except Exception as e:
                            logger.warning(f"Failed to decode email payload: {e}")
                            body = "Unable to decode email content"

                    # Get email timestamp for better filtering
                    email_date = msg["date"]
                    replies.append({
                        "from": msg["from"],
                        "subject": subject,
                        "body": body,
                        "date": email_date,
                        "message_id": msg.get("Message-ID", ""),
                        "thread_id": msg.get("X-Thread-ID", "")
                    })
                    # Note: Not marking as read for testing purposes

            mail.logout()
        except Exception as e:
            logger.error("Failed to check for replies", error=str(e))

        if replies:
            logger.info(f"Found {len(replies)} new replies from {prospect_email}")
            # Sort by date (most recent first) for better processing
            try:
                from email.utils import parsedate_to_datetime
                from datetime import datetime
                replies.sort(key=lambda x: parsedate_to_datetime(x["date"]) if x["date"] else datetime.min, reverse=True)
            except:
                pass  # If date parsing fails, keep original order
        return replies

# Global instance
email_mcp = EmailMCP()
