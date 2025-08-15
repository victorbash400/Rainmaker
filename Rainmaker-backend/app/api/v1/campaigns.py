"""
Campaigns API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import Campaign, User
from app.db.schemas import (
    Campaign as CampaignSchema,
    CampaignCreate,
    PaginatedResponse
)
from app.api.deps import get_current_active_user


router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_campaigns(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    channel: Optional[str] = None,
    prospect_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get paginated list of campaigns"""
    query = select(Campaign)
    
    # Apply filters
    if status:
        query = query.where(Campaign.status == status)
    if channel:
        query = query.where(Campaign.channel == channel)
    if prospect_id:
        query = query.where(Campaign.prospect_id == prospect_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Campaign.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    campaigns = result.scalars().all()
    
    return {
        "items": campaigns,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


@router.get("/{campaign_id}", response_model=CampaignSchema)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific campaign by ID"""
    query = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign


@router.post("/", response_model=CampaignSchema)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new campaign"""
    db_campaign = Campaign(**campaign_data.dict())
    db.add(db_campaign)
    await db.commit()
    await db.refresh(db_campaign)
    
    return db_campaign


@router.post("/{campaign_id}/approve")
async def approve_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Approve a campaign for sending"""
    query = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Campaign is not pending approval")
    
    campaign.status = "approved"
    campaign.approved_by = current_user.email
    
    await db.commit()
    await db.refresh(campaign)
    
    return {"message": "Campaign approved successfully", "campaign": campaign}