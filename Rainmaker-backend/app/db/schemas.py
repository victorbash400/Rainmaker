"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# Enums
class ProspectType(str, Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"


class ProspectStatus(str, Enum):
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class EventType(str, Enum):
    WEDDING = "wedding"
    CORPORATE_EVENT = "corporate_event"
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    GRADUATION = "graduation"
    OTHER = "other"


# Base schemas
class ProspectBase(BaseModel):
    prospect_type: ProspectType
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    source: str


class ProspectCreate(ProspectBase):
    pass


class ProspectUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[ProspectStatus] = None
    lead_score: Optional[int] = None
    assigned_to: Optional[str] = None


class Prospect(ProspectBase):
    id: int
    status: ProspectStatus
    lead_score: int
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Event Requirements schemas
class EventRequirementsBase(BaseModel):
    event_type: EventType
    event_date: Optional[datetime] = None
    guest_count: Optional[int] = None
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    location_preference: Optional[str] = None
    venue_type: Optional[str] = None
    special_requirements: Optional[str] = None
    style_preferences: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    accessibility_needs: Optional[str] = None


class EventRequirementsCreate(EventRequirementsBase):
    prospect_id: int


class EventRequirements(EventRequirementsBase):
    id: int
    prospect_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Campaign schemas
class CampaignBase(BaseModel):
    channel: str
    campaign_type: str
    subject_line: Optional[str] = None
    message_body: str
    personalization_data: Optional[Dict[str, Any]] = None


class CampaignCreate(CampaignBase):
    prospect_id: int


class Campaign(CampaignBase):
    id: int
    prospect_id: int
    status: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    replied_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Conversation schemas
class ConversationBase(BaseModel):
    channel: str
    conversation_summary: Optional[str] = None
    extracted_requirements: Optional[Dict[str, Any]] = None
    sentiment_score: Optional[Decimal] = None
    qualification_score: int = 0
    next_action: Optional[str] = None


class ConversationCreate(ConversationBase):
    prospect_id: int


class Conversation(ConversationBase):
    id: int
    prospect_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Message schemas
class MessageBase(BaseModel):
    sender_type: str
    sender_name: Optional[str] = None
    message_content: str
    message_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    conversation_id: int


class Message(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Proposal schemas
class ProposalBase(BaseModel):
    proposal_name: str
    total_price: Decimal
    guest_count: int
    event_date: datetime
    venue_details: Optional[Dict[str, Any]] = None
    package_details: Optional[Dict[str, Any]] = None
    terms_conditions: Optional[str] = None
    valid_until: datetime


class ProposalCreate(ProposalBase):
    prospect_id: int


class Proposal(ProposalBase):
    id: int
    prospect_id: int
    proposal_pdf_url: Optional[str]
    mood_board_url: Optional[str]
    status: str
    approved_by: Optional[str]
    sent_at: Optional[datetime]
    viewed_at: Optional[datetime]
    responded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Meeting schemas
class MeetingBase(BaseModel):
    meeting_type: str
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int = 60
    location: Optional[str] = None
    meeting_url: Optional[str] = None
    attendees: Optional[Dict[str, Any]] = None
    agenda: Optional[str] = None


class MeetingCreate(MeetingBase):
    prospect_id: int


class Meeting(MeetingBase):
    id: int
    prospect_id: int
    calendar_event_id: Optional[str]
    notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "sales_rep"


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Response schemas
class ApiResponse(BaseModel):
    data: Any
    message: Optional[str] = None
    success: bool = True


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int