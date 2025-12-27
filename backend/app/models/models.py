import uuid
import enum
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import String, DateTime, Enum, ForeignKey, Column, Table, Text, Numeric, Float, Boolean, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from app.core.database import Base
except ImportError:
    from app.core.database import Base

# --- Enums ---

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TWG_FACILITATOR = "twg_facilitator"
    TWG_MEMBER = "twg_member"
    SECRETARIAT_LEAD = "secretariat_lead"

class TWGPillar(str, enum.Enum):
    energy_infrastructure = "energy_infrastructure"
    agriculture_food_systems = "agriculture_food_systems"
    critical_minerals_industrialization = "critical_minerals_industrialization"
    digital_economy_transformation = "digital_economy_transformation"
    protocol_logistics = "protocol_logistics"
    resource_mobilization = "resource_mobilization"

class MeetingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class MinutesStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    FINAL = "final"

class ActionItemStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"

class ActionItemPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ProjectStatus(str, enum.Enum):
    IDENTIFIED = "identified"
    VETTING = "vetting"
    BANKABLE = "bankable"
    PRESENTED = "presented"

class NotificationType(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ALERT = "alert"
    MESSAGE = "message"
    DOCUMENT = "document"
    TASK = "task"

# --- Association Tables ---

twg_members = Table(
    "twg_members",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("twg_id", Uuid, ForeignKey("twgs.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime, default=datetime.utcnow)
)

meeting_participants = Table(
    "meeting_participants",
    Base.metadata,
    Column("meeting_id", Uuid, ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("rsvp_status", String(50), default="pending"), # pending, accepted, declined
    Column("attended", Boolean, default=False)
)

# --- Models ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.TWG_MEMBER)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    twgs: Mapped[List["TWG"]] = relationship(
        secondary=twg_members, back_populates="members"
    )
    owned_action_items: Mapped[List["ActionItem"]] = relationship(back_populates="owner")
    meetings: Mapped[List["Meeting"]] = relationship(
        secondary=meeting_participants, back_populates="participants"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Notification.created_at.desc()"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(255))
    resource_type: Mapped[str] = mapped_column(String(100)) # e.g., "meeting", "document", "project"
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # Contextual info
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

class TWG(Base):
    __tablename__ = "twgs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    pillar: Mapped[TWGPillar] = mapped_column(Enum(TWGPillar))
    status: Mapped[str] = mapped_column(String(50), default="active")
    
    political_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    technical_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    members: Mapped[List["User"]] = relationship(
        secondary=twg_members, back_populates="twgs"
    )
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="twg")
    projects: Mapped[List["Project"]] = relationship(back_populates="twg")
    action_items: Mapped[List["ActionItem"]] = relationship(back_populates="twg")
    documents: Mapped[List["Document"]] = relationship(back_populates="twg")

class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    title: Mapped[str] = mapped_column(String(255))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(default=60)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    meeting_type: Mapped[str] = mapped_column(String(50), default="virtual") # virtual, in-person
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Text or link to transcript
    
    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="meetings")
    participants: Mapped[List["User"]] = relationship(
        secondary=meeting_participants, back_populates="meetings"
    )
    agenda: Mapped[Optional["Agenda"]] = relationship(back_populates="meeting", uselist=False)
    minutes: Mapped[Optional["Minutes"]] = relationship(back_populates="meeting", uselist=False)
    action_items: Mapped[List["ActionItem"]] = relationship(back_populates="meeting")

class Agenda(Base):
    __tablename__ = "agendas"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("meetings.id"), unique=True)
    content: Mapped[str] = mapped_column(Text) # Markdown or HTML
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="agenda")

class Minutes(Base):
    __tablename__ = "minutes"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("meetings.id"), unique=True)
    content: Mapped[str] = mapped_column(Text) # Markdown or HTML
    key_decisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[MinutesStatus] = mapped_column(Enum(MinutesStatus), default=MinutesStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="minutes")

class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("meetings.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    due_date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[ActionItemStatus] = mapped_column(Enum(ActionItemStatus), default=ActionItemStatus.PENDING)
    priority: Mapped[ActionItemPriority] = mapped_column(Enum(ActionItemPriority), default=ActionItemPriority.MEDIUM)
    
    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="action_items")
    meeting: Mapped[Optional["Meeting"]] = relationship(back_populates="action_items")
    owner: Mapped["User"] = relationship(back_populates="owned_action_items")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    investment_size: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.IDENTIFIED)
    investment_memo_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="projects")
    investment_memo: Mapped[Optional["Document"]] = relationship(foreign_keys=[investment_memo_id])

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("twgs.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(255))  # MIME type can be long
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    twg: Mapped[Optional["TWG"]] = relationship(back_populates="documents")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), default=NotificationType.INFO)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")
