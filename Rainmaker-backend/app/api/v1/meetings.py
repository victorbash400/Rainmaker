"""
Meetings API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import Meeting, User
from app.db.schemas import (
    Meeting as MeetingSchema,
    MeetingCreate,
    PaginatedResponse
)
from app.api.deps import get_current_active_user


router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_meetings(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    meeting_type: Optional[str] = None,
    prospect_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get paginated list of meetings"""
    query = select(Meeting)
    
    # Apply filters
    if status:
        query = query.where(Meeting.status == status)
    if meeting_type:
        query = query.where(Meeting.meeting_type == meeting_type)
    if prospect_id:
        query = query.where(Meeting.prospect_id == prospect_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Meeting.scheduled_at.desc())
    
    # Execute query
    result = await db.execute(query)
    meetings = result.scalars().all()
    
    return {
        "items": meetings,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


@router.get("/{meeting_id}", response_model=MeetingSchema)
async def get_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific meeting by ID"""
    query = select(Meeting).where(Meeting.id == meeting_id)
    result = await db.execute(query)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    return meeting


@router.post("/", response_model=MeetingSchema)
async def create_meeting(
    meeting_data: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new meeting"""
    db_meeting = Meeting(**meeting_data.dict())
    db.add(db_meeting)
    await db.commit()
    await db.refresh(db_meeting)
    
    return db_meeting


@router.put("/{meeting_id}/status")
async def update_meeting_status(
    meeting_id: int,
    status: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update meeting status"""
    query = select(Meeting).where(Meeting.id == meeting_id)
    result = await db.execute(query)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    meeting.status = status
    if notes:
        meeting.notes = notes
    
    await db.commit()
    await db.refresh(meeting)
    
    return {"message": "Meeting status updated successfully", "meeting": meeting}