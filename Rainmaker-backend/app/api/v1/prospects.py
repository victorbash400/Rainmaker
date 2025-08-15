"""
Prospects API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Prospect, User
from app.db.schemas import (
    Prospect as ProspectSchema,
    ProspectCreate,
    ProspectUpdate,
    ApiResponse,
    PaginatedResponse
)
from app.api.deps import get_current_active_user


router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_prospects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    prospect_type: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get paginated list of prospects"""
    query = select(Prospect)
    
    # Apply filters
    if status:
        query = query.where(Prospect.status == status)
    if prospect_type:
        query = query.where(Prospect.prospect_type == prospect_type)
    if search:
        query = query.where(
            Prospect.name.ilike(f"%{search}%") |
            Prospect.email.ilike(f"%{search}%") |
            Prospect.company_name.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    prospects = result.scalars().all()
    
    return {
        "items": prospects,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


@router.get("/{prospect_id}", response_model=ProspectSchema)
async def get_prospect(
    prospect_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific prospect by ID"""
    query = select(Prospect).where(Prospect.id == prospect_id)
    result = await db.execute(query)
    prospect = result.scalar_one_or_none()
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    return prospect


@router.post("/", response_model=ProspectSchema)
async def create_prospect(
    prospect_data: ProspectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new prospect"""
    db_prospect = Prospect(**prospect_data.dict())
    db.add(db_prospect)
    await db.commit()
    await db.refresh(db_prospect)
    
    return db_prospect


@router.put("/{prospect_id}", response_model=ProspectSchema)
async def update_prospect(
    prospect_id: int,
    prospect_data: ProspectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a prospect"""
    query = select(Prospect).where(Prospect.id == prospect_id)
    result = await db.execute(query)
    prospect = result.scalar_one_or_none()
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    # Update fields
    update_data = prospect_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prospect, field, value)
    
    await db.commit()
    await db.refresh(prospect)
    
    return prospect


@router.delete("/{prospect_id}")
async def delete_prospect(
    prospect_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a prospect"""
    query = select(Prospect).where(Prospect.id == prospect_id)
    result = await db.execute(query)
    prospect = result.scalar_one_or_none()
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    await db.delete(prospect)
    await db.commit()
    
    return {"message": "Prospect deleted successfully"}