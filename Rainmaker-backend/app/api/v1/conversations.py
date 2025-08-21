"""
Conversations API endpoints for email message tracking
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.db.models import User, EmailMessage, Prospect
from app.db.schemas import ConversationResponse, EmailMessageCreate, EmailMessageResponse
from sqlalchemy import desc, func

router = APIRouter()
logger = structlog.get_logger(__name__)

@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ConversationResponse]:
    """
    Get all conversations (grouped by workflow_id) for the current user
    """
    logger.info("API: Getting conversations", user_id=current_user.id)
    
    try:
        # Get all workflows with email messages for this user
        conversations_data = db.query(
            EmailMessage.workflow_id,
            EmailMessage.recipient_email,
            func.count(EmailMessage.id).label('message_count'),
            func.max(EmailMessage.timestamp).label('last_timestamp')
        ).filter(
            EmailMessage.user_id == current_user.id
        ).group_by(
            EmailMessage.workflow_id,
            EmailMessage.recipient_email
        ).all()
        
        conversations = []
        
        for conv_data in conversations_data:
            workflow_id = conv_data.workflow_id
            prospect_email = conv_data.recipient_email
            
            # Get all messages for this conversation
            messages = db.query(EmailMessage).filter(
                EmailMessage.workflow_id == workflow_id,
                EmailMessage.user_id == current_user.id
            ).order_by(EmailMessage.timestamp.asc()).all()
            
            if not messages:
                continue
                
            # Get prospect info if available
            prospect = None
            if messages[0].prospect_id:
                prospect = db.query(Prospect).filter(Prospect.id == messages[0].prospect_id).first()
            
            # Get last message for preview
            last_message = max(messages, key=lambda m: m.timestamp)
            
            # Determine status based on message flow
            status = "waiting"  # Default
            if any(msg.direction == "received" for msg in messages[-3:]):  # Recent reply
                status = "active"
            elif last_message.message_type in ["calendar_invite"] and last_message.timestamp:
                status = "completed"
            
            conversation = ConversationResponse(
                workflow_id=workflow_id,
                prospect_name=prospect.name if prospect else None,
                prospect_email=prospect_email,
                prospect_company=prospect.company_name if prospect else None,
                message_count=len(messages),
                last_message=last_message.body[:100] + "..." if len(last_message.body) > 100 else last_message.body,
                last_timestamp=last_message.timestamp,
                status=status,
                messages=[EmailMessageResponse.from_orm(msg) for msg in messages]
            )
            
            conversations.append(conversation)
        
        # Sort by last message timestamp (most recent first)
        conversations.sort(key=lambda c: c.last_timestamp, reverse=True)
        
        logger.info("Conversations retrieved successfully", 
                   user_id=current_user.id, 
                   count=len(conversations))
        
        return conversations
        
    except Exception as e:
        logger.error("Failed to get conversations", 
                    user_id=current_user.id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")


@router.get("/{workflow_id}", response_model=ConversationResponse)
async def get_conversation(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ConversationResponse:
    """
    Get a specific conversation by workflow_id
    """
    logger.info("API: Getting conversation", workflow_id=workflow_id, user_id=current_user.id)
    
    try:
        # Get all messages for this workflow
        messages = db.query(EmailMessage).filter(
            EmailMessage.workflow_id == workflow_id,
            EmailMessage.user_id == current_user.id
        ).order_by(EmailMessage.timestamp.asc()).all()
        
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get prospect info if available
        prospect = None
        if messages[0].prospect_id:
            prospect = db.query(Prospect).filter(Prospect.id == messages[0].prospect_id).first()
        
        # Get last message
        last_message = max(messages, key=lambda m: m.timestamp)
        
        # Determine status
        status = "waiting"
        if any(msg.direction == "received" for msg in messages[-3:]):
            status = "active"
        elif last_message.message_type == "calendar_invite":
            status = "completed"
        
        conversation = ConversationResponse(
            workflow_id=workflow_id,
            prospect_name=prospect.name if prospect else None,
            prospect_email=messages[0].recipient_email,
            prospect_company=prospect.company_name if prospect else None,
            message_count=len(messages),
            last_message=last_message.body[:100] + "..." if len(last_message.body) > 100 else last_message.body,
            last_timestamp=last_message.timestamp,
            status=status,
            messages=[EmailMessageResponse.from_orm(msg) for msg in messages]
        )
        
        logger.info("Conversation retrieved successfully", workflow_id=workflow_id)
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation", 
                    workflow_id=workflow_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.post("/save-email", response_model=EmailMessageResponse)
async def save_email_message(
    email_data: EmailMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> EmailMessageResponse:
    """
    Save an email message to the conversation history
    This endpoint is used by agents to record sent/received emails
    """
    logger.info("API: Saving email message", 
               workflow_id=email_data.workflow_id,
               direction=email_data.direction,
               message_type=email_data.message_type)
    
    try:
        # Create the email message
        db_message = EmailMessage(
            **email_data.dict(),
            user_id=current_user.id
        )
        
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        logger.info("Email message saved successfully", 
                   message_id=db_message.id,
                   workflow_id=email_data.workflow_id)
        
        return EmailMessageResponse.from_orm(db_message)
        
    except Exception as e:
        logger.error("Failed to save email message", 
                    workflow_id=email_data.workflow_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save email message: {str(e)}")