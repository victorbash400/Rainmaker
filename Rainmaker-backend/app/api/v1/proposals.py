"""
Proposals API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import Proposal, User
from app.db.schemas import (
    Proposal as ProposalSchema,
    ProposalCreate,
    PaginatedResponse
)
from app.api.deps import get_current_active_user


router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_proposals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    prospect_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get paginated list of proposals"""
    query = select(Proposal)
    
    # Apply filters
    if status:
        query = query.where(Proposal.status == status)
    if prospect_id:
        query = query.where(Proposal.prospect_id == prospect_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Proposal.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    proposals = result.scalars().all()
    
    return {
        "items": proposals,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


@router.get("/{proposal_id}", response_model=ProposalSchema)
async def get_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific proposal by ID"""
    query = select(Proposal).where(Proposal.id == proposal_id)
    result = await db.execute(query)
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return proposal


@router.post("/", response_model=ProposalSchema)
async def create_proposal(
    proposal_data: ProposalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new proposal"""
    db_proposal = Proposal(**proposal_data.dict())
    db.add(db_proposal)
    await db.commit()
    await db.refresh(db_proposal)
    
    return db_proposal


@router.post("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Approve a proposal for sending"""
    query = select(Proposal).where(Proposal.id == proposal_id)
    result = await db.execute(query)
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Proposal is not pending approval")
    
    proposal.status = "sent"
    proposal.approved_by = current_user.email
    
    await db.commit()
    await db.refresh(proposal)
    
    return {"message": "Proposal approved and sent successfully", "proposal": proposal}