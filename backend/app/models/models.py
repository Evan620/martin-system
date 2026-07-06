import uuid
import enum
from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Enum, ForeignKey, Column, Table, Text, Numeric, Float, Boolean, JSON, Uuid, Integer, ARRAY, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from app.core.database import Base
except ImportError:
    from app.core.database import Base

# --- Enums ---

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    TWG_FACILITATOR = "TWG_FACILITATOR"
    TWG_MEMBER = "TWG_MEMBER"
    SECRETARIAT_LEAD = "SECRETARIAT_LEAD"

class TWGPillar(str, enum.Enum):
    energy_infrastructure = "energy_infrastructure"
    agriculture_food_systems = "agriculture_food_systems"
    critical_minerals_industrialization = "critical_minerals_industrialization"
    digital_economy_transformation = "digital_economy_transformation"
    protocol_logistics = "protocol_logistics"
    resource_mobilization = "resource_mobilization"

class MeetingStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"  # New: Pending Supervisor approval
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS" # Added: Currently live/active
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

class RsvpStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    TENTATIVE = "TENTATIVE"

class MinutesStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    FINAL = "FINAL"

class ActionItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"

class ActionItemPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ProjectStatus(str, enum.Enum):
    # Pre-Pipeline
    INCUBATION = "INCUBATION"

    # Submission Phase
    DRAFT = "DRAFT"
    PIPELINE = "PIPELINE"
    UNDER_REVIEW = "UNDER_REVIEW"

    # Decision Phase
    DECLINED = "DECLINED"
    NEEDS_REVISION = "NEEDS_REVISION"
    SUMMIT_READY = "SUMMIT_READY"

    # Deal Room Phase
    DEAL_ROOM_FEATURED = "DEAL_ROOM_FEATURED"
    IN_NEGOTIATION = "IN_NEGOTIATION"

    # Post-Deal Phase
    COMMITTED = "COMMITTED"
    IMPLEMENTED = "IMPLEMENTED"

    # Other
    ON_HOLD = "ON_HOLD"
    ARCHIVED = "ARCHIVED"

class NotificationType(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ALERT = "alert"
    MESSAGE = "message"
    DOCUMENT = "document"
    TASK = "task"

class ConflictType(str, enum.Enum):
    SCHEDULE_CLASH = "SCHEDULE_CLASH"
    RESOURCE_CONSTRAINT = "RESOURCE_CONSTRAINT"
    POLICY_MISALIGNMENT = "POLICY_MISALIGNMENT"
    DEPENDENCY_BLOCKER = "DEPENDENCY_BLOCKER"
    VIP_AVAILABILITY = "VIP_AVAILABILITY"
    PROJECT_DEPENDENCY_CONFLICT = "PROJECT_DEPENDENCY_CONFLICT"
    DUPLICATE_PROJECT_CONFLICT = "DUPLICATE_PROJECT_CONFLICT"

class ConflictSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ConflictStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    NEGOTIATING = "NEGOTIATING"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"

class DependencyStatus(str, enum.Enum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"

class InvestorMatchStatus(str, enum.Enum):
    DETECTED = "detected"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    NEGOTIATING = "negotiating"
    COMMITTED = "committed"


class BuyerMatchStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    CONTACTED = "CONTACTED"
    INTERESTED = "INTERESTED"
    NEGOTIATING = "NEGOTIATING"
    COMMITTED = "COMMITTED"

class DependencyType(str, enum.Enum):
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"

class DependencySource(str, enum.Enum):
    TWG_PACKET = "twg_packet"
    AI_INFERRED = "ai_inferred"
    MANUAL = "manual"

class OrganizationInvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

class InvitationMessageSender(str, enum.Enum):
    ADMIN = "admin"
    INVITEE = "invitee"

class RecurrenceFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"

class RecurrenceEndType(str, enum.Enum):
    AFTER_DATE = "after_date"
    AFTER_OCCURRENCES = "after_occurrences"
    NEVER = "never"

class RecurringMeetingStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    CANCELLED = "cancelled"

# --- Association Tables ---

twg_members = Table(
    "twg_members",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("twg_id", Uuid, ForeignKey("twgs.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime, default=datetime.utcnow),
    extend_existing=True
)

subgroup_members = Table(
    "subgroup_members",
    Base.metadata,
    Column("subgroup_id", Uuid, ForeignKey("subgroups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime, default=datetime.utcnow),
    extend_existing=True
)

class MeetingDependency(Base):
    __tablename__ = "meeting_dependencies"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("meetings.id", ondelete="CASCADE"))
    target_meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("meetings.id", ondelete="CASCADE"))
    
    dependency_type: Mapped[DependencyType] = mapped_column(Enum(DependencyType), default=DependencyType.FINISH_TO_START)
    lag_minutes: Mapped[int] = mapped_column(Integer, default=0)
    
    # Source Tracking
    source_type: Mapped[DependencySource] = mapped_column(Enum(DependencySource), default=DependencySource.MANUAL)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    created_by_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g. "EnergyAgent"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    source_meeting: Mapped["Meeting"] = relationship("Meeting", foreign_keys=[source_meeting_id], back_populates="successors")
    target_meeting: Mapped["Meeting"] = relationship("Meeting", foreign_keys=[target_meeting_id], back_populates="predecessors")

# MeetingParticipant Class (Association Object)
class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("meetings.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    rsvp_status: Mapped[RsvpStatus] = mapped_column(Enum(RsvpStatus), default=RsvpStatus.PENDING)
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="participants")
    user: Mapped[Optional["User"]] = relationship(back_populates="meeting_participations")


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(String(500))
    remind_at: Mapped[datetime] = mapped_column(DateTime)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- Models ---

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.TWG_MEMBER)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    invite_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invite_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    twgs: Mapped[List["TWG"]] = relationship(
        secondary=twg_members, back_populates="members"
    )

    @property
    def twg_ids(self) -> List[uuid.UUID]:
        return [twg.id for twg in self.twgs]
    
    owned_action_items: Mapped[List["ActionItem"]] = relationship(back_populates="owner")
    meeting_participations: Mapped[List["MeetingParticipant"]] = relationship(back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Notification.created_at.desc()"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")
    
    # VIP Profile (One-to-One)
    vip_profile: Mapped[Optional["VipProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")

class VipProfile(Base):
    """
    Profile for Very Important Persons (Ministers, Heads of State, etc.)
    Tracks their priority level and availability constraints.
    """
    __tablename__ = "vip_profiles"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    title: Mapped[str] = mapped_column(String(100)) # e.g. "Minister of Energy"
    priority_level: Mapped[int] = mapped_column(Integer, default=1) # 1=Standard, 5=Head of State
    companies: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Companies/Orgs they represent
    
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # e.g. "No morning meetings"
    calendar_sync_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="vip_profile")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

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
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    pillar: Mapped[TWGPillar] = mapped_column(Enum(TWGPillar))
    status: Mapped[str] = mapped_column(String(50), default="active")
    group_type: Mapped[str] = mapped_column(String(50), default="twg")  # "twg" or "leads_council"
    
    political_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    technical_lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    political_lead: Mapped[Optional["User"]] = relationship("User", foreign_keys=[political_lead_id])
    technical_lead: Mapped[Optional["User"]] = relationship("User", foreign_keys=[technical_lead_id])

    members: Mapped[List["User"]] = relationship(
        secondary=twg_members, back_populates="twgs"
    )
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="twg")
    projects: Mapped[List["Project"]] = relationship(back_populates="twg")
    action_items: Mapped[List["ActionItem"]] = relationship(back_populates="twg")
    documents: Mapped[List["Document"]] = relationship(back_populates="twg")
    subgroups: Mapped[List["SubGroup"]] = relationship("SubGroup", back_populates="twg", cascade="all, delete-orphan")
    recurring_meetings: Mapped[List["RecurringMeeting"]] = relationship(back_populates="twg")

    # Dependencies
    dependencies_as_source: Mapped[List["Dependency"]] = relationship("Dependency", foreign_keys="[Dependency.source_twg_id]", back_populates="source_twg")
    dependencies_as_target: Mapped[List["Dependency"]] = relationship("Dependency", foreign_keys="[Dependency.target_twg_id]", back_populates="target_twg")

class SubGroup(Base):
    __tablename__ = "subgroups"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id", ondelete="CASCADE"))
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    twg: Mapped["TWG"] = relationship("TWG", back_populates="subgroups")
    lead: Mapped[Optional["User"]] = relationship("User", foreign_keys=[lead_id])
    members: Mapped[List["User"]] = relationship("User", secondary=subgroup_members)
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="subgroup")

class Dependency(Base):
    """
    Tracks cross-TWG dependencies.
    Example: Minerals TWG (source) must decide on 'smelting_policy' 
    before Energy TWG (target) can schedule 'power_planning'
    """
    __tablename__ = "dependencies"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    
    source_twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    target_twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[DependencyStatus] = mapped_column(Enum(DependencyStatus), default=DependencyStatus.PENDING)
    
    # Optional links to blocking artifacts
    blocking_meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("meetings.id"), nullable=True)
    blocking_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    source_twg: Mapped["TWG"] = relationship("TWG", foreign_keys=[source_twg_id], back_populates="dependencies_as_source")
    target_twg: Mapped["TWG"] = relationship("TWG", foreign_keys=[target_twg_id], back_populates="dependencies_as_target")
    blocking_meeting: Mapped[Optional["Meeting"]] = relationship("Meeting")
    blocking_document: Mapped[Optional["Document"]] = relationship("Document")

class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    subgroup_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("subgroups.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(default=60)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    meeting_type: Mapped[str] = mapped_column(String(50), default="virtual") # virtual, in-person
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Text or link to transcript
    video_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True) # Google Meet / Zoom link
    attendee_bot_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Attendee bot ID for transcript retrieval

    # Recurring Meeting Fields
    recurring_meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("recurring_meetings.id", ondelete="SET NULL"), nullable=True
    )
    is_recurring_exception: Mapped[bool] = mapped_column(Boolean, default=False)
    original_scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="meetings")
    subgroup: Mapped[Optional["SubGroup"]] = relationship("SubGroup")
    participants: Mapped[List["MeetingParticipant"]] = relationship(
        "MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan"
    )
    agenda: Mapped[Optional["Agenda"]] = relationship(back_populates="meeting", uselist=False)
    minutes: Mapped[Optional["Minutes"]] = relationship(back_populates="meeting", uselist=False)
    action_items: Mapped[List["ActionItem"]] = relationship(back_populates="meeting")
    documents: Mapped[List["Document"]] = relationship(back_populates="meeting")

    # Dependency Graph Relationships
    successors: Mapped[List["MeetingDependency"]] = relationship(
        "MeetingDependency",
        foreign_keys="[MeetingDependency.source_meeting_id]",
        back_populates="source_meeting",
        cascade="all, delete-orphan"
    )
    predecessors: Mapped[List["MeetingDependency"]] = relationship(
        "MeetingDependency",
        foreign_keys="[MeetingDependency.target_meeting_id]",
        back_populates="target_meeting",
        cascade="all, delete-orphan"
    )

    # Recurring Meeting Relationship
    recurring_parent: Mapped[Optional["RecurringMeeting"]] = relationship(back_populates="instances")

class RecurringMeeting(Base):
    """
    Template for recurring meetings that automatically generates Meeting instances.
    Uses a parent-child pattern where this is the template and Meeting instances are children.
    """
    __tablename__ = "recurring_meetings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))

    # Template fields (copied to each instance)
    title_template: Mapped[str] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(default=60)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meeting_type: Mapped[str] = mapped_column(String(50), default="virtual")

    # Recurrence Configuration
    frequency: Mapped[RecurrenceFrequency] = mapped_column(
        Enum(RecurrenceFrequency, values_callable=lambda x: [e.value for e in x])
    )
    interval_weeks: Mapped[int] = mapped_column(Integer, default=1)
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0=Mon, 6=Sun

    # Start/End Configuration
    start_date: Mapped[datetime] = mapped_column(DateTime)
    start_time: Mapped[str] = mapped_column(String(10))  # "14:00" format
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    end_type: Mapped[RecurrenceEndType] = mapped_column(
        Enum(RecurrenceEndType, values_callable=lambda x: [e.value for e in x])
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    max_occurrences: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # State
    status: Mapped[RecurringMeetingStatus] = mapped_column(
        Enum(RecurringMeetingStatus, values_callable=lambda x: [e.value for e in x]),
        default=RecurringMeetingStatus.ACTIVE
    )
    occurrences_created: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    created_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="recurring_meetings")
    instances: Mapped[List["Meeting"]] = relationship(back_populates="recurring_parent")
    created_by: Mapped["User"] = relationship("User")

class Agenda(Base):
    __tablename__ = "agendas"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("meetings.id"), unique=True)
    content: Mapped[str] = mapped_column(Text) # Markdown or HTML
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="agenda")

class MinutesVersion(Base):
    __tablename__ = "minutes_versions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    minutes_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("minutes.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    key_decisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    action_items_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    minutes: Mapped["Minutes"] = relationship(back_populates="versions")
    author: Mapped["User"] = relationship(foreign_keys=[created_by])


class Minutes(Base):
    __tablename__ = "minutes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("meetings.id"), unique=True)
    content: Mapped[str] = mapped_column(Text) # Markdown or HTML
    key_decisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Chair-approved public summary — the ONLY minutes data emitted to Campaign OS.
    # Shape: {"highlights": [], "decisions_milestones": [], "institutions_public": [], "next_milestone": ""}
    public_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[MinutesStatus] = mapped_column(Enum(MinutesStatus, values_callable=lambda x: [e.value for e in x]), default=MinutesStatus.DRAFT)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Version control fields
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    last_edited_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    last_edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="minutes")
    versions: Mapped[List["MinutesVersion"]] = relationship(back_populates="minutes", cascade="all, delete-orphan")
    editor: Mapped[Optional["User"]] = relationship(foreign_keys=[last_edited_by])

class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    subgroup_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("subgroups.id", ondelete="SET NULL"), nullable=True)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("meetings.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    raw_owner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Raw owner name from minutes before fuzzy-matching
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[ActionItemStatus] = mapped_column(Enum(ActionItemStatus), default=ActionItemStatus.PENDING)
    priority: Mapped[ActionItemPriority] = mapped_column(Enum(ActionItemPriority), default=ActionItemPriority.MEDIUM)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="action_items")
    subgroup: Mapped[Optional["SubGroup"]] = relationship("SubGroup")
    meeting: Mapped[Optional["Meeting"]] = relationship(back_populates="action_items")
    owner: Mapped[Optional["User"]] = relationship(back_populates="owned_action_items")

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    investment_size: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    investment_memo_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Deal Pipeline fields
    pillar: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lead_country: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    afcen_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    strategic_alignment_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    assigned_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Financials
    funding_secured_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=0)
    
    # Deal Room Flags
    is_flagship: Mapped[bool] = mapped_column(Boolean, default=False)
    deal_room_priority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Investment Template Fields — Section A
    subsector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    project_sponsor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_cross_border: Mapped[bool] = mapped_column(Boolean, default=False)
    key_contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    key_contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Investment Template Fields — Section B
    technical_studies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permits_licences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    land_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Investment Template Fields — Section C
    financing_structure: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    investment_stage_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    revenue_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    macroeconomic_roi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Investment Template Fields — Section D
    climate_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    esg_compliance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ghg_avoided_target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jobs_construction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jobs_om: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    electricity_connections: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    digital_connections: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    smallholder_farmers_reached: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Investment Template Fields — Section A (Classification — Phase 1)
    value_chain_stages: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    # Sector-specific bespoke intake fields for non-agribusiness sectors
    # (energy / minerals / digital). Shape is defined by frontend sectorConfig.ts;
    # stored verbatim. Agribusiness continues to use its dedicated columns above.
    sector_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    women_employment_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    youth_employment_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Gender & Youth intentional design flags (R2 — Carren benchmark)
    gender_intentional: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    gender_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youth_focused: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    youth_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # R6 — Certifications the project holds (Fairtrade, Organic, Rainforest Alliance,
    # UTZ, GlobalG.A.P., EU GAP). Matched against buyer.certifications_accepted to
    # score offtake fit. Optional — many early-stage projects won't have any yet.
    certifications_held: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # R8 — Site coordinates for geospatial analysis (NDVI, water proximity,
    # land-use classification, deforestation risk). Optional — set by the
    # project owner; triggers `geospatial_service.analyse_project()` on rescore.
    site_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    site_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Human-readable place name (e.g., "Bondoukou rural, Côte d'Ivoire"). Set
    # by the sponsor at intake via the site-location picker, or auto-scouted
    # from the project content and confirmed by a facilitator. Independent
    # from lat/lon — the coords are authoritative for analysis.
    site_location_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Submission metadata
    submitted_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps (these columns exist in the DB schema; mapped here so the
    # ORM can read/write them, e.g. for the R5 90-day stale-incubation check).
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="projects")
    investment_memo: Mapped[Optional["Document"]] = relationship(foreign_keys=[investment_memo_id])
    investor_matches: Mapped[List["ProjectInvestorMatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    buyer_matches: Mapped[List["ProjectBuyerMatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    dfi_matches: Mapped[List["ProjectDFIMatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    impact_log_entries: Mapped[List["ImpactLogEntry"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    geospatial_data: Mapped[Optional["ProjectGeospatialData"]] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship(foreign_keys="[Document.project_id]", back_populates="project")
    score_details: Mapped[List["ProjectScoreDetail"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    status_history: Mapped[List["ProjectStatusHistory"]] = relationship(back_populates="project", cascade="all, delete-orphan")

class ProjectInterest(Base):
    """A member following / expressing interest in a Deal Room project.

    One row per (project, user) — the unique constraint makes the
    POST /pipeline/{id}/interest endpoint idempotent at the DB level.
    """
    __tablename__ = "project_interests"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_interest_project_user"),
        {'extend_existing': True},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project")
    user: Mapped["User"] = relationship("User")


class ProjectStatusHistory(Base):
    __tablename__ = "project_status_history"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    
    # Status Change
    previous_status: Mapped[Optional[ProjectStatus]] = mapped_column(Enum(ProjectStatus), nullable=True)
    new_status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus))
    
    # Who changed it
    changed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Why changed
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Automated vs Manual
    is_automated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="status_history")
    changed_by: Mapped[Optional["User"]] = relationship("User")

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("twgs.id"), nullable=True)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("meetings.id"), nullable=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True)
    subgroup_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("subgroups.id", ondelete="SET NULL"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(255))  # MIME type can be long
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g. financial_model, esia
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    twg: Mapped[Optional["TWG"]] = relationship(back_populates="documents")
    meeting: Mapped[Optional["Meeting"]] = relationship(foreign_keys=[meeting_id], back_populates="documents")
    project: Mapped[Optional["Project"]] = relationship(foreign_keys=[project_id], back_populates="documents")
    subgroup: Mapped[Optional["SubGroup"]] = relationship("SubGroup", back_populates="documents")

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Knowledge Broadcasting
    scope: Mapped[List[str]] = mapped_column(JSON, default=["twg_restricted"]) 
    category: Mapped[str] = mapped_column(String(50), default="twg_specific")
    last_broadcast: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    access_control: Mapped[str] = mapped_column(String(50), default="twg_restricted")
    parent_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=True)

    # Relationships
    parent_document: Mapped[Optional["Document"]] = relationship("Document", remote_side="Document.id", back_populates="versions")
    versions: Mapped[List["Document"]] = relationship("Document", back_populates="parent_document", cascade="all, delete-orphan")

    uploaded_by: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by_id])

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

class PasswordResetToken(Base):
    """Stores password reset tokens for forgot password functionality."""
    __tablename__ = "password_reset_tokens"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship()

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

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

class Conflict(Base):
    __tablename__ = "conflicts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conflict_type: Mapped[ConflictType] = mapped_column(Enum(ConflictType))
    severity: Mapped[ConflictSeverity] = mapped_column(Enum(ConflictSeverity))
    description: Mapped[str] = mapped_column(Text)
    agents_involved: Mapped[List[str]] = mapped_column(JSON) # List of agent names
    conflicting_positions: Mapped[dict] = mapped_column(JSON) # Key: agent name, Value: position description
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # New field for extra context
    
    status: Mapped[ConflictStatus] = mapped_column(Enum(ConflictStatus), default=ConflictStatus.DETECTED)
    resolution_log: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True) # History of negotiation
    human_action_required: Mapped[bool] = mapped_column(Boolean, default=False)
    
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class WeeklyPacket(Base):
    __tablename__ = "weekly_packets"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    week_start_date: Mapped[datetime] = mapped_column(DateTime)
    
    # Structured Data (stored as JSON)
    proposed_sessions: Mapped[List[dict]] = mapped_column(JSON) # List of proposed meetings
    dependencies: Mapped[List[dict]] = mapped_column(JSON) # Identified cross-TWG dependencies
    accomplishments: Mapped[List[str]] = mapped_column(JSON) # Bullet points of achievements
    risks_and_blockers: Mapped[List[dict]] = mapped_column(JSON) # Identified risks
    
    status: Mapped[str] = mapped_column(String(50), default="draft") # draft, submitted, ingested
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    twg: Mapped["TWG"] = relationship("TWG")


class Investor(Base):
    """
    Investor entity for the Deal Pipeline.
    Tracks investor preferences and criteria for project matching.
    """
    __tablename__ = "investors"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    sector_preferences: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    ticket_size_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    ticket_size_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    geographic_focus: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    investment_instruments: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Extended Fields
    investor_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_commitments_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=0)

    # Mandate signals — mirror DFIWindow so investor matching can consume the same
    # project signals (value chain, gender, youth, climate) that DFI matching already uses.
    value_chain_preferences: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    gender_focus: Mapped[bool] = mapped_column(Boolean, default=False)
    youth_focus: Mapped[bool] = mapped_column(Boolean, default=False)
    climate_focus: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project_matches: Mapped[List["ProjectInvestorMatch"]] = relationship(back_populates="investor", cascade="all, delete-orphan")


class ProjectInvestorMatch(Base):
    """
    Match between a Project and an Investor.
    Tracks match score and status through the deal flow.
    """
    __tablename__ = "project_investor_matches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    investor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("investors.id", ondelete="CASCADE"))
    
    match_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[InvestorMatchStatus] = mapped_column(Enum(InvestorMatchStatus), default=InvestorMatchStatus.DETECTED)
    meeting_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="investor_matches")
    investor: Mapped["Investor"] = relationship(back_populates="project_matches")


class Buyer(Base):
    __tablename__ = "buyers"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    commodity_types: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    volume_mt_per_year: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    contract_term_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_floor_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geographic_focus: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    # R6 — Certifications the buyer requires from suppliers (Fairtrade, Rainforest Alliance,
    # Organic, UTZ, EU GAP, GlobalG.A.P., etc.). Matches against project.certifications_held.
    certifications_accepted: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    # R6 — DEMO / VERIFIED status so seeded buyers aren't confused with real signed partners
    verification_status: Mapped[str] = mapped_column(String(20), default="demo", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buyer_matches: Mapped[List["ProjectBuyerMatch"]] = relationship(back_populates="buyer", cascade="all, delete-orphan")


class ProjectBuyerMatch(Base):
    __tablename__ = "project_buyer_matches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    buyer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("buyers.id", ondelete="CASCADE"))
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[BuyerMatchStatus] = mapped_column(Enum(BuyerMatchStatus), default=BuyerMatchStatus.DETECTED)
    match_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="buyer_matches")
    buyer: Mapped["Buyer"] = relationship(back_populates="buyer_matches")


class DFIMatchStatus(str, enum.Enum):
    IDENTIFIED = "IDENTIFIED"
    APPROACHED = "APPROACHED"
    IN_REVIEW = "IN_REVIEW"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DFIInstrumentType(str, enum.Enum):
    GRANT = "GRANT"
    CONCESSIONAL_LOAN = "CONCESSIONAL_LOAN"
    EQUITY = "EQUITY"
    BLENDED = "BLENDED"


class DFIWindow(Base):
    __tablename__ = "dfi_windows"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    institution: Mapped[str] = mapped_column(String(255))
    instrument_type: Mapped[DFIInstrumentType] = mapped_column(Enum(DFIInstrumentType), default=DFIInstrumentType.BLENDED)
    sectors: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    geographies: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    min_size_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_size_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eligible_stages: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    gender_focus: Mapped[bool] = mapped_column(Boolean, default=False)
    climate_focus: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Polish 2 — FK linking this window to its parent Investor record. Nullable so
    # legacy windows continue to work pre-backfill; populated by
    # scripts/link_dfi_windows_to_investors.py via string-matching institution names.
    investor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("investors.id", ondelete="SET NULL"), nullable=True,
    )
    # R7 — Concessional eligibility rules. Free-form JSON so each window can express
    # its own conditions without a schema migration per rule type. Common keys:
    #   max_project_size_usd, min_project_size_usd, allowed_lead_countries (list),
    #   excluded_lead_countries (list), required_pillar (list), required_value_chain (list),
    #   requires_gender_intentional (bool), requires_climate_target (bool),
    #   max_lead_country_gdp_per_capita_usd (int).
    # The eligibility filter in dfi_matching_service evaluates these against the
    # project; a window failing any rule is marked eligible=false with a reason.
    concessional_eligibility_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dfi_matches: Mapped[List["ProjectDFIMatch"]] = relationship(back_populates="dfi_window", cascade="all, delete-orphan")


class ProjectDFIMatch(Base):
    __tablename__ = "project_dfi_matches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    dfi_window_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("dfi_windows.id", ondelete="CASCADE"))
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    fit_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DFIMatchStatus] = mapped_column(Enum(DFIMatchStatus), default=DFIMatchStatus.IDENTIFIED)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="dfi_matches")
    dfi_window: Mapped["DFIWindow"] = relationship(back_populates="dfi_matches")
    # R7 — Eligibility evaluation cached per match row so we don't re-run rules
    # on every read. Set when matching runs; rationale is human-readable.
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    ineligibility_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class BlendedFinancePackage(Base):
    """R7 — A multi-tranche blended finance structure for a project, generated by
    the AI financing memo workflow and refinable by an admin. One project may
    have many packages (different scenarios); the most recently saved one is the
    'active' recommendation. Tranches are first-class child rows so the structure
    can be validated (e.g. amounts sum to investment ask, first-loss < concessional)."""

    __tablename__ = "blended_finance_packages"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), default="AI-generated package")
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_amount_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="llm")  # 'llm' | 'default_fallback' | 'manual'
    error_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tranches: Mapped[List["BlendedFinanceTranche"]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="BlendedFinanceTranche.seniority",
    )


class BlendedFinanceTranche(Base):
    """R7 — One layer in a blended finance capital stack.

    Seniority convention: lower number = more senior. So senior debt = 1,
    mezzanine = 2, first-loss equity / grant = 3. Senior tranches are repaid first
    in a downside scenario; first-loss absorbs initial losses to protect commercial
    capital and is what makes the package 'blended'.
    """

    __tablename__ = "blended_finance_tranches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("blended_finance_packages.id", ondelete="CASCADE"))
    dfi_window_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("dfi_windows.id", ondelete="SET NULL"), nullable=True)

    label: Mapped[str] = mapped_column(String(255))  # human-readable, e.g. "AfDB ADPP senior concessional"
    instrument_type: Mapped[DFIInstrumentType] = mapped_column(Enum(DFIInstrumentType), default=DFIInstrumentType.BLENDED)
    amount_usd: Mapped[float] = mapped_column(Float)
    tenor_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    coupon_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seniority: Mapped[int] = mapped_column(Integer, default=1)  # 1=senior, larger=more junior
    is_first_loss: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    package: Mapped["BlendedFinancePackage"] = relationship(back_populates="tranches")
    dfi_window: Mapped[Optional["DFIWindow"]] = relationship()


class ScoringCriteria(Base):
    __tablename__ = "scoring_criteria"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    criterion_name: Mapped[str] = mapped_column(String(100))
    criterion_type: Mapped[str] = mapped_column(String(50)) # 'readiness' or 'strategic_fit'
    weight: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class ProjectScoreDetail(Base):
    __tablename__ = "project_scores_detail"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    criterion_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scoring_criteria.id"))
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # 0-100
    scored_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id"))
    scored_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="score_details")

class DealRoomMeeting(Base):
    __tablename__ = "deal_room_meetings"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    investor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("investors.id", ondelete="CASCADE"))
    
    meeting_datetime: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    meeting_status: Mapped[str] = mapped_column(String(50), default='scheduled')
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scheduled_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id"))

class SystemSettings(Base):
    """
    Singleton table for global system configuration.
    Only editable by Admins.
    """
    __tablename__ = "system_settings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    
    # Integrations
    enable_google_calendar: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_zoom: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_teams: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Credentials (Stored as Text/JSON - Encrypt in Prod)
    google_credentials_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    zoom_credentials_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    teams_credentials_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # AI Configuration
    llm_provider: Mapped[str] = mapped_column(String(50), default="openai") # openai, github, gemini
    llm_model: Mapped[str] = mapped_column(String(50), default="gpt-4o-mini")
    
    # Email
    smtp_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

class TwgSettings(Base):
    """
    Settings specific to a single TWG workspace.
    Editable by Admin or assigned Facilitator.
    """
    __tablename__ = "twg_settings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id", ondelete="CASCADE"), unique=True)
    
    # Preferences
    meeting_cadence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # weekly, biweekly, monthly
    custom_templates: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # Email/Doc templates overrides
    notification_preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # Defaults for members
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    twg: Mapped["TWG"] = relationship("TWG")


class PlatformSetting(Base):
    """Key/value store for admin-configurable platform settings (e.g. gender/youth thresholds)."""
    __tablename__ = "platform_settings"
    __table_args__ = {'extend_existing': True}

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrganizationInvitation(Base):
    """
    Invitations sent to external organizations to join TWGs.
    Tracks invitation status through pending, accepted, declined, expired states.
    """
    __tablename__ = "organization_invitations"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_name: Mapped[str] = mapped_column(String(255))
    contact_email: Mapped[str] = mapped_column(String(255), index=True)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id"))
    custom_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[OrganizationInvitationStatus] = mapped_column(
        Enum(OrganizationInvitationStatus), default=OrganizationInvitationStatus.PENDING
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    last_resend_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Unread message counts for quick lookup
    unread_by_admin_count: Mapped[int] = mapped_column(Integer, default=0)
    unread_by_invitee_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    twg: Mapped["TWG"] = relationship("TWG")
    created_by: Mapped["User"] = relationship("User")
    messages: Mapped[List["InvitationMessage"]] = relationship(
        back_populates="invitation", cascade="all, delete-orphan", order_by="InvitationMessage.created_at"
    )


class InvitationMessage(Base):
    """
    Messages exchanged between admins and invitees within an invitation thread.
    """
    __tablename__ = "invitation_messages"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    invitation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organization_invitations.id", ondelete="CASCADE"))
    sender_type: Mapped[InvitationMessageSender] = mapped_column(Enum(InvitationMessageSender))
    sender_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_name: Mapped[str] = mapped_column(String(255))  # Display name (admin name or organization name)
    content: Mapped[str] = mapped_column(Text)
    is_read_by_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read_by_invitee: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    invitation: Mapped["OrganizationInvitation"] = relationship(back_populates="messages")
    sender_user: Mapped[Optional["User"]] = relationship("User")


class ImpactLogEntry(Base):
    """R9 — Post-commitment quarterly impact tracking. One row per project per
    reporting period. Targets come from the parent Project's columns; this table
    stores the actuals."""

    __tablename__ = "impact_log_entries"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    period_label: Mapped[str] = mapped_column(Text)  # "Q1 2026"
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)

    # Actuals
    jobs_created: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ghg_avoided_tco2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    smallholders_reached: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    women_jobs_actual: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    youth_jobs_actual: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investment_deployed_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    logged_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="impact_log_entries")
    logged_by: Mapped["User"] = relationship("User", foreign_keys=[logged_by_id])


class ProjectGeospatialData(Base):
    """R8 — Cached geospatial analysis for a project. One row per project.
    Generated on demand by geospatial_service.analyse_project(); refreshed on
    rescore or coordinate change. STUB IMPLEMENTATION — `is_demo=true` until
    real Copernicus / AfCEN integration lands."""

    __tablename__ = "project_geospatial_data"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    ndvi: Mapped[float] = mapped_column(Float)
    water_proximity_km: Mapped[float] = mapped_column(Float)
    land_use_description: Mapped[str] = mapped_column(Text)
    land_use_smallholder_pct: Mapped[float] = mapped_column(Float)
    deforestation_risk: Mapped[str] = mapped_column(Text)  # 'low' | 'medium' | 'high'
    geo_score_boost: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="stub", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    analysed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="geospatial_data")


class AgentAuditLog(Base):
    """One row per Martin-executed write. Pairs with project_status_history
    for stage moves but is the catch-all for everything else."""
    __tablename__ = "agent_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    before_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
