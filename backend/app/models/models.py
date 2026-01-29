import uuid
import enum
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import String, DateTime, Enum, ForeignKey, Column, Table, Text, Numeric, Float, Boolean, JSON, Uuid, Integer
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
    
    # Legacy Statuses (Mapped to new ones where possible, but kept for safety)
    IDENTIFIED = "identified"      # -> DRAFT or PIPELINE
    VETTING = "vetting"            # -> UNSER_REVIEW
    DUE_DILIGENCE = "due_diligence" # -> UNDER_REVIEW
    FINANCING = "financing"         # -> SUMMIT_READY
    DEAL_ROOM = "deal_room"        # -> SUMMIT_READY / DEAL_ROOM_FEATURED
    BANKABLE = "bankable"          # -> COMMITTED
    PRESENTED = "presented"        # -> DEAL_ROOM_FEATURED

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

class DependencyType(str, enum.Enum):
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"

class DependencySource(str, enum.Enum):
    TWG_PACKET = "twg_packet"
    AI_INFERRED = "ai_inferred"
    MANUAL = "manual"

# --- Association Tables ---

twg_members = Table(
    "twg_members",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("twg_id", Uuid, ForeignKey("twgs.id", ondelete="CASCADE"), primary_key=True),
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
    
    # Dependencies
    dependencies_as_source: Mapped[List["Dependency"]] = relationship("Dependency", foreign_keys="[Dependency.source_twg_id]", back_populates="source_twg")
    dependencies_as_target: Mapped[List["Dependency"]] = relationship("Dependency", foreign_keys="[Dependency.target_twg_id]", back_populates="target_twg")

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
    title: Mapped[str] = mapped_column(String(255))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(default=60)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    meeting_type: Mapped[str] = mapped_column(String(50), default="virtual") # virtual, in-person
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Text or link to transcript
    video_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True) # Google Meet / Zoom link
    
    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="meetings")
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
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("meetings.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[ActionItemStatus] = mapped_column(Enum(ActionItemStatus), default=ActionItemStatus.PENDING)
    priority: Mapped[ActionItemPriority] = mapped_column(Enum(ActionItemPriority), default=ActionItemPriority.MEDIUM)
    
    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="action_items")
    meeting: Mapped[Optional["Meeting"]] = relationship(back_populates="action_items")
    owner: Mapped["User"] = relationship(back_populates="owned_action_items")

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
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.IDENTIFIED)
    investment_memo_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Deal Pipeline fields
    pillar: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lead_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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

    # Relationships
    twg: Mapped["TWG"] = relationship(back_populates="projects")
    investment_memo: Mapped[Optional["Document"]] = relationship(foreign_keys=[investment_memo_id])
    investor_matches: Mapped[List["ProjectInvestorMatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship(foreign_keys="[Document.project_id]", back_populates="project")
    score_details: Mapped[List["ProjectScoreDetail"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    status_history: Mapped[List["ProjectStatusHistory"]] = relationship(back_populates="project", cascade="all, delete-orphan")

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
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(255))  # MIME type can be long
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g. financial_model, esia
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    twg: Mapped[Optional["TWG"]] = relationship(back_populates="documents")
    meeting: Mapped[Optional["Meeting"]] = relationship(foreign_keys=[meeting_id], back_populates="documents")
    project: Mapped[Optional["Project"]] = relationship(foreign_keys=[project_id], back_populates="documents")

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
    score: Mapped[Decimal] = mapped_column(Numeric(3, 1)) # 0-10
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
