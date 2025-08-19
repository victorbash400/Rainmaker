"""
SQLAlchemy database models
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.sql.sqltypes import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class ProspectType(str, enum.Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"


class ProspectStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class EventType(str, enum.Enum):
    WEDDING = "wedding"
    CORPORATE_EVENT = "corporate_event"
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    GRADUATION = "graduation"
    OTHER = "other"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    REJECTED = "rejected"


class CampaignPlanStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Prospect(Base):
    __tablename__ = "prospects"
    
    id = Column(Integer, primary_key=True, index=True)
    prospect_type = Column(Enum(ProspectType), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), index=True)
    phone = Column(String(50))
    company_name = Column(String(255))
    location = Column(String(255))
    source = Column(String(100), nullable=False)
    status = Column(Enum(ProspectStatus), default=ProspectStatus.DISCOVERED)
    lead_score = Column(Integer, default=0)
    assigned_to = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    event_requirements = relationship("EventRequirements", back_populates="prospect")
    campaigns = relationship("Campaign", back_populates="prospect")
    conversations = relationship("Conversation", back_populates="prospect")
    proposals = relationship("Proposal", back_populates="prospect")
    meetings = relationship("Meeting", back_populates="prospect")


class EventRequirements(Base):
    __tablename__ = "event_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    event_date = Column(DateTime)
    guest_count = Column(Integer)
    budget_min = Column(Numeric(10, 2))
    budget_max = Column(Numeric(10, 2))
    location_preference = Column(String(255))
    venue_type = Column(String(100))
    special_requirements = Column(Text)
    style_preferences = Column(Text)
    dietary_restrictions = Column(Text)
    accessibility_needs = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    prospect = relationship("Prospect", back_populates="event_requirements")


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    channel = Column(Enum("email", "linkedin", "phone", "in_person", name="campaign_channel"), nullable=False)
    campaign_type = Column(String(100), nullable=False)
    subject_line = Column(String(255))
    message_body = Column(Text, nullable=False)
    personalization_data = Column(JSON)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    replied_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    prospect = relationship("Prospect", back_populates="campaigns")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    channel = Column(Enum("email", "chat", "phone", "in_person", name="conversation_channel"), nullable=False)
    conversation_summary = Column(Text)
    extracted_requirements = Column(JSON)
    sentiment_score = Column(Numeric(3, 2))  # -1.0 to 1.0
    qualification_score = Column(Integer, default=0)  # 0-100
    next_action = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    prospect = relationship("Prospect", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_type = Column(Enum("prospect", "agent", "human", name="sender_type"), nullable=False)
    sender_name = Column(String(255))
    message_content = Column(Text, nullable=False)
    message_type = Column(Enum("text", "email", "attachment", "system", name="message_type"), default="text")
    message_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    proposal_name = Column(String(255), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    guest_count = Column(Integer, nullable=False)
    event_date = Column(DateTime, nullable=False)
    venue_details = Column(JSON)
    package_details = Column(JSON)
    terms_conditions = Column(Text)
    proposal_pdf_url = Column(String(500))
    mood_board_url = Column(String(500))
    status = Column(Enum("draft", "pending_approval", "sent", "viewed", "accepted", "rejected", "negotiating", "expired", name="proposal_status"), default="draft")
    approved_by = Column(String(255))
    sent_at = Column(DateTime(timezone=True))
    viewed_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))
    valid_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    prospect = relationship("Prospect", back_populates="proposals")


class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(255), index=True)  # Added for workflow tracking
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Added user tracking
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=True)  # Made nullable
    prospect_name = Column(String(255), nullable=False)  # Added for direct storage
    prospect_email = Column(String(255), nullable=False)  # Added for direct storage
    prospect_company = Column(String(255))  # Added for direct storage
    meeting_type = Column(Enum("initial_call", "venue_visit", "planning_session", "final_walkthrough", "consultation", name="meeting_type"), default="consultation")
    title = Column(String(255), nullable=False)
    description = Column(Text)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=60)
    location = Column(String(255))
    meeting_url = Column(String(500))
    google_meet_link = Column(String(500))  # Added specifically for Google Meet
    calendar_event_id = Column(String(255))
    attendees = Column(JSON)
    agenda = Column(Text)
    notes = Column(Text)
    status = Column(Enum("scheduled", "confirmed", "completed", "cancelled", "rescheduled", name="meeting_status"), default="scheduled")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    prospect = relationship("Prospect", back_populates="meetings")
    user = relationship("User")


class AgentActivity(Base):
    __tablename__ = "agent_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=False)
    activity_type = Column(String(100), nullable=False)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="SET NULL"))
    description = Column(Text, nullable=False)
    input_data = Column(JSON)
    output_data = Column(JSON)
    status = Column(Enum("started", "completed", "failed", "cancelled", name="activity_status"), nullable=False)
    error_message = Column(Text)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum("admin", "sales_rep", "manager", name="user_role"), default="sales_rep")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    campaign_plans = relationship("CampaignPlan", back_populates="user")


class CampaignPlan(Base):
    __tablename__ = "campaign_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    campaign_name = Column(String(255), nullable=False)
    objectives = Column(JSON, nullable=False)
    target_profile = Column(JSON, nullable=False)
    execution_strategy = Column(JSON, nullable=False)
    expected_timeline = Column(JSON)
    resource_requirements = Column(JSON)
    risk_factors = Column(JSON)
    success_predictions = Column(JSON)
    status = Column(Enum(CampaignPlanStatus), default=CampaignPlanStatus.DRAFT)
    execution_started_at = Column(DateTime(timezone=True))
    execution_completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="campaign_plans")