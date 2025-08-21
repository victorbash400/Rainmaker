"""
Email tracking service for recording email conversations
"""
import requests
import structlog
from datetime import datetime
from typing import Optional, Dict, Any

logger = structlog.get_logger(__name__)

class EmailTracker:
    """Simple service to track sent and received emails for conversations"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def save_sent_email(
        self,
        workflow_id: str,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
        message_type: str,  # "outreach", "follow_up", "calendar_invite", "overview_request"
        prospect_id: Optional[int] = None,
        user_token: Optional[str] = None
    ) -> bool:
        """
        Save a sent email to conversation history
        
        Args:
            workflow_id: The workflow this email belongs to
            sender_email: Email address of sender (agent)
            recipient_email: Email address of recipient (prospect)
            subject: Email subject line
            body: Email content
            message_type: Type of message (outreach, follow_up, calendar_invite, overview_request)
            prospect_id: Optional prospect ID if known
            user_token: Optional auth token (for API calls)
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            email_data = {
                "workflow_id": workflow_id,
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "direction": "sent",
                "message_type": message_type,
                "timestamp": datetime.now().isoformat(),
                "prospect_id": prospect_id
            }
            
            headers = {}
            if user_token:
                headers["Authorization"] = f"Bearer {user_token}"
            
            # For now, just log the email - in production you'd call the API
            logger.info("Email sent - saving to conversation history",
                       workflow_id=workflow_id,
                       message_type=message_type,
                       recipient=recipient_email,
                       subject=subject[:50] + "..." if len(subject) > 50 else subject)
            
            # TODO: Make API call to save email
            # response = requests.post(f"{self.base_url}/api/v1/conversations/save-email", 
            #                         json=email_data, headers=headers)
            # return response.status_code == 200
            
            return True
            
        except Exception as e:
            logger.error("Failed to save sent email", 
                        workflow_id=workflow_id,
                        error=str(e))
            return False
    
    def save_received_email(
        self,
        workflow_id: str,
        sender_email: str,  # Prospect email
        recipient_email: str,  # Agent email  
        subject: str,
        body: str,
        prospect_id: Optional[int] = None,
        user_token: Optional[str] = None
    ) -> bool:
        """
        Save a received email to conversation history
        
        Args:
            workflow_id: The workflow this email belongs to
            sender_email: Email address of sender (prospect)
            recipient_email: Email address of recipient (agent)
            subject: Email subject line
            body: Email content
            prospect_id: Optional prospect ID if known
            user_token: Optional auth token (for API calls)
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            email_data = {
                "workflow_id": workflow_id,
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "direction": "received",
                "message_type": "reply",
                "timestamp": datetime.now().isoformat(),
                "prospect_id": prospect_id
            }
            
            headers = {}
            if user_token:
                headers["Authorization"] = f"Bearer {user_token}"
            
            # For now, just log the email - in production you'd call the API
            logger.info("Email received - saving to conversation history",
                       workflow_id=workflow_id,
                       sender=sender_email,
                       subject=subject[:50] + "..." if len(subject) > 50 else subject)
            
            # TODO: Make API call to save email
            # response = requests.post(f"{self.base_url}/api/v1/conversations/save-email", 
            #                         json=email_data, headers=headers)
            # return response.status_code == 200
            
            return True
            
        except Exception as e:
            logger.error("Failed to save received email", 
                        workflow_id=workflow_id,
                        error=str(e))
            return False

# Global instance
email_tracker = EmailTracker()