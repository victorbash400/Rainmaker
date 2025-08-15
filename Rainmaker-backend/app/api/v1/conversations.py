"""
Conversations API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Conversation, Message, User
from app.db.schemas import (
    Conversation as ConversationSchema,
    ConversationCreate,
    Message as MessageSchema,
    MessageCreate,
    PaginatedResponse
)
from app.api.deps import get_current_active_user


router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    prospect_id: Optional[int] = None,
    channel: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get paginated list of conversations"""
    query = select(Conversation)
    
    # Apply filters
    if prospect_id:
        query = query.where(Conversation.prospect_id == prospect_id)
    if channel:
        query = query.where(Conversation.channel == channel)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Conversation.updated_at.desc())
    
    # Execute query
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    return {
        "items": conversations,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


@router.get("/{conversation_id}", response_model=ConversationSchema)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific conversation by ID"""
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.post("/", response_model=ConversationSchema)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new conversation"""
    db_conversation = Conversation(**conversation_data.dict())
    db.add(db_conversation)
    await db.commit()
    await db.refresh(db_conversation)
    
    return db_conversation


@router.get("/{conversation_id}/messages", response_model=List[MessageSchema])
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all messages in a conversation"""
    query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return messages


@router.post("/{conversation_id}/messages", response_model=MessageSchema)
async def create_message(
    conversation_id: int,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a message to a conversation"""
    # Verify conversation exists
    conv_query = select(Conversation).where(Conversation.id == conversation_id)
    conv_result = await db.execute(conv_query)
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create message
    message_dict = message_data.dict()
    message_dict["conversation_id"] = conversation_id
    db_message = Message(**message_dict)
    
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    
    return db_message