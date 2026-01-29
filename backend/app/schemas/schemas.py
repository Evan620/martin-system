from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Any
from decimal import Decimal
import uuid
import enum

# --- Enums (mirrored from models) ---

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    TWG_FACILITATOR = "TWG_FACILITATOR"
    TWG_MEMBER = "TWG_MEMBER"
    SECRETARIAT_LEAD = "SECRETARIAT_LEAD"

class TWGPillar(str, enum.Enum):
    ENERGY_INFRASTRUCTURE = "energy_infrastructure"
    AGRICULTURE_FOOD_SYSTEMS = "agriculture_food_systems"
    CRITICAL_MINERALS_INDUSTRIALIZATION = "critical_minerals_industrialization"
    DIGITAL_ECONOMY_TRANSFORMATION = "digital_economy_transformation"
    PROTOCOL_LOGISTICS = "protocol_logistics"
    RESOURCE_MOBILIZATION = "resource_mobilization"

class MeetingStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

class RsvpStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"

class MinutesStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    REVIEW = "review"
    APPROVED = "approved"
    FINAL = "final"

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
    IDENTIFIED = "IDENTIFIED"
    VETTING = "VETTING"
    DUE_DILIGENCE = "DUE_DILIGENCE"
    FINANCING = "FINANCING"
    DEAL_ROOM = "DEAL_ROOM"
    BANKABLE = "BANKABLE"
    PRESENTED = "PRESENTED"

class NotificationType(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ALERT = "alert"
    MESSAGE = "message"
    DOCUMENT = "document"
    TASK = "task"

class DocumentStage(str, enum.Enum):
    ZERO_DRAFT = "zero_draft"
    RAP_MODE = "rap_mode"
    DECLARATION_TXT = "declaration_txt"
    FINAL = "final"

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

class DependencyType(str, enum.Enum):
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"
    FINISH_TO_FINISH = "finish_to_finish"
    START_TO_FINISH = "start_to_finish"

# --- Base Schema ---

class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- User Schemas ---

class UserBase(SchemaBase):
    full_name: str
    email: EmailStr
    role: UserRole = UserRole.TWG_MEMBER
    organization: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(SchemaBase):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    organization: Optional[str] = None

class TWGRef(SchemaBase):
    id: uuid.UUID
    name: str

class UserSimple(UserBase):
    id: uuid.UUID
    
class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    twgs: List[TWGRef] = []

# --- TWG Schemas ---

class TWGBase(SchemaBase):
    name: str
    pillar: TWGPillar
    status: str = "active"
    political_lead_id: Optional[uuid.UUID] = None
    technical_lead_id: Optional[uuid.UUID] = None

class TWGCreate(TWGBase):
    pass

class TWGUpdate(SchemaBase):
    name: Optional[str] = None
    pillar: Optional[TWGPillar] = None
    status: Optional[str] = None
    political_lead_id: Optional[uuid.UUID] = None
    technical_lead_id: Optional[uuid.UUID] = None

class TWGStats(SchemaBase):
    meetings_held: int
    open_actions: int
    pipeline_projects: int
    resources_count: int

class TWGRead(TWGBase):
    id: uuid.UUID
    political_lead: Optional["UserSimple"] = None
    technical_lead: Optional["UserSimple"] = None
    members: List["UserSimple"] = []
    stats: Optional[TWGStats] = None
    # Removed action_items and documents to prevent MissingGreenlet errors

# --- Document Schemas ---

class DocumentBase(SchemaBase):
    twg_id: Optional[uuid.UUID] = None
    file_name: str
    file_type: str
    stage: str = "final" # Relaxed from DocumentStage
    is_confidential: bool = False
    metadata_json: Optional[dict] = None

class DocumentCreate(DocumentBase):
    file_path: str
    uploaded_by_id: uuid.UUID

class DocumentRead(DocumentBase):
    id: uuid.UUID
    file_path: str
    uploaded_by_id: uuid.UUID
    uploaded_by: Optional["UserSimple"] = None
    twg: Optional["TWGBase"] = None
    ingested_at: Optional[datetime] = None
    created_at: datetime

# --- Meeting Schemas ---

class MeetingBase(SchemaBase):
    twg_id: uuid.UUID
    title: str
    scheduled_at: datetime
    duration_minutes: int = 60
    location: Optional[str] = None
    status: MeetingStatus = MeetingStatus.SCHEDULED
    meeting_type: str = "virtual"
    transcript: Optional[str] = None

class MeetingCreate(MeetingBase):
    pass

class MeetingUpdate(SchemaBase):
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    status: Optional[MeetingStatus] = None
    meeting_type: Optional[str] = None
    transcript: Optional[str] = None

class MeetingCancel(SchemaBase):
    reason: Optional[str] = None
    notify_participants: bool = True

class MeetingUpdateNotification(SchemaBase):
    changes: List[str] = []
    notify_participants: bool = True

class InviteStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"

class InvitePreview(SchemaBase):
    """Preview of meeting invitation before sending"""
    meeting_id: uuid.UUID
    subject: str
    html_content: str
    participants: List[str]  # List of email addresses
    ics_attached: bool = True
    status: InviteStatus = InviteStatus.DRAFT

# --- Meeting Participant Schema ---

class MeetingParticipantRead(SchemaBase):
    id: uuid.UUID
    meeting_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    email: Optional[str] = None
    rsvp_status: RsvpStatus = RsvpStatus.PENDING
    attended: bool = False
    
    # Nested user details if available
    user: Optional["UserSimple"] = None

class MeetingParticipantCreate(SchemaBase):
    user_id: Optional[uuid.UUID] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None

class MeetingParticipantUpdate(SchemaBase):
    rsvp_status: Optional[RsvpStatus] = None

class DependencySource(str, enum.Enum):
    TWG_PACKET = "twg_packet"
    AI_INFERRED = "ai_inferred"
    MANUAL = "manual"

class MeetingDependencyRead(SchemaBase):
    id: uuid.UUID
    source_meeting_id: uuid.UUID
    target_meeting_id: uuid.UUID
    dependency_type: DependencyType
    lag_minutes: int
    
    # Source Tracking
    source_type: DependencySource = DependencySource.MANUAL
    confidence_score: float = 1.0
    created_by_agent: Optional[str] = None
    
    # Optional names for UI display
    source_meeting_title: Optional[str] = None
    target_meeting_title: Optional[str] = None

class MeetingRead(MeetingBase):
    id: uuid.UUID
    video_link: Optional[str] = None
    twg: Optional["TWGBase"] = None
    participants: List[MeetingParticipantRead] = []
    documents: List["DocumentRead"] = []
    # Optional: only populated when fetching a single meeting with eager loading
    successors: Optional[List[MeetingDependencyRead]] = None
    predecessors: Optional[List[MeetingDependencyRead]] = None

# --- Agenda Schemas ---

class AgendaBase(SchemaBase):
    content: str

class AgendaCreate(AgendaBase):
    pass

class AgendaUpdate(SchemaBase):
    content: Optional[str] = None

class AgendaRead(AgendaBase):
    id: uuid.UUID
    meeting_id: uuid.UUID
    created_at: datetime


# --- Minutes Schemas ---

class MinutesBase(SchemaBase):
    content: str
    key_decisions: Optional[str] = None
    status: str = "draft" # Relaxed from MinutesStatus

class MinutesCreate(MinutesBase):
    meeting_id: uuid.UUID

class MinutesUpdate(SchemaBase):
    content: Optional[str] = None
    key_decisions: Optional[str] = None
    status: Optional[MinutesStatus] = None

class MinutesUpdateWithVersion(MinutesUpdate):
    """Extended update schema that includes change summary for version control"""
    change_summary: Optional[str] = None

class MinutesRejectionRequest(SchemaBase):
    reason: str
    suggested_changes: Optional[str] = None

class MinutesVersionRead(SchemaBase):
    """Schema for reading a specific version of minutes"""
    id: uuid.UUID
    version_number: int
    content: str
    key_decisions: Optional[str] = None
    change_summary: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    author: Optional["UserSimple"] = None

class MinutesRead(MinutesBase):
    id: uuid.UUID
    meeting_id: uuid.UUID
    created_at: datetime
    rejection_reason: Optional[str] = None
    rejected_at: Optional[datetime] = None
    # Version control fields
    current_version: int = 1
    last_edited_by: Optional[uuid.UUID] = None
    last_edited_at: Optional[datetime] = None
    editor: Optional["UserSimple"] = None

# --- Action Item Schemas ---

class ActionItemBase(SchemaBase):
    twg_id: uuid.UUID
    meeting_id: Optional[uuid.UUID] = None
    description: str
    owner_id: uuid.UUID
    due_date: datetime
    status: ActionItemStatus = ActionItemStatus.PENDING
    priority: ActionItemPriority = ActionItemPriority.MEDIUM

class ActionItemCreate(ActionItemBase):
    pass

class ActionItemRead(ActionItemBase):
    id: uuid.UUID
    owner: Optional["UserRead"] = None

# --- Project Schemas ---

class ProjectBase(SchemaBase):
    twg_id: uuid.UUID
    name: str
    description: str
    investment_size: float
    currency: str = "USD"
    readiness_score: float = 0.0
    afcen_score: Optional[Decimal] = None
    strategic_alignment_score: Optional[Decimal] = None
    status: ProjectStatus = ProjectStatus.IDENTIFIED
    investment_memo_id: Optional[uuid.UUID] = None
    metadata_json: Optional[dict] = None
    funding_secured_usd: Decimal = 0
    is_flagship: bool = False
    deal_room_priority: Optional[int] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectRead(ProjectBase):
    id: uuid.UUID



# --- Notification Schemas ---

class NotificationBase(SchemaBase):
    type: NotificationType = NotificationType.INFO
    title: str
    content: str
    link: Optional[str] = None
    is_read: bool = False

class NotificationCreate(NotificationBase):
    user_id: uuid.UUID

class NotificationUpdate(SchemaBase):
    is_read: Optional[bool] = None

class NotificationRead(NotificationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

# --- Auth Schemas ---

class Token(SchemaBase):
    access_token: str
    token_type: str

class TokenData(SchemaBase):
    email: Optional[str] = None

# --- Audit Schemas ---

class AuditLogRead(SchemaBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[uuid.UUID] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

# --- Agent Interaction Schemas ---

class AgentChatRequest(SchemaBase):
    message: str
    conversation_id: Optional[uuid.UUID] = None
    twg_id: Optional[uuid.UUID] = None

class AgentChatResponse(SchemaBase):
    response: str
    conversation_id: uuid.UUID
    citations: List[dict] = []
    agent_id: str
    interrupted: Optional[bool] = False
    interrupt_payload: Optional[dict] = None
    thread_id: Optional[str] = None
    suggestions: List[str] = []

class AgentTaskRequest(SchemaBase):
    task_type: str # drafting, research, analysis, synthesis
    twg_id: uuid.UUID
    details: dict
    title: str

class AgentStatus(SchemaBase):
    status: str
    swarm_ready: bool
    swarm_ready: bool
    version: str

class DocumentApprovalRequest(SchemaBase):
    title: str
    content: str
    document_type: str
    file_name: str
    tags: List[str] = []
    
class DocumentApprovalResult(SchemaBase):
    status: str
    document_id: str
    file_path: str
    message: str

# --- Conflict Schemas ---

class ConflictBase(SchemaBase):
    conflict_type: ConflictType
    severity: ConflictSeverity
    description: str
    agents_involved: List[str] # List of agent names
    conflicting_positions: dict # Key: agent name, Value: position description
    status: ConflictStatus = ConflictStatus.DETECTED
    resolution_log: Optional[List[dict]] = None
    human_action_required: bool = False

class ConflictCreate(ConflictBase):
    pass

class ConflictUpdate(SchemaBase):
    status: Optional[ConflictStatus] = None
    resolution_log: Optional[List[dict]] = None
    human_action_required: Optional[bool] = None
    resolved_at: Optional[datetime] = None

class ConflictRead(ConflictBase):
    id: uuid.UUID
    detected_at: datetime
    resolved_at: Optional[datetime] = None

class ManualConflictResolution(BaseModel):
    resolution_type: str # "reschedule" or "cancel"
    meeting_id: uuid.UUID
    new_time: Optional[datetime] = None
    reason: Optional[str] = "Manual Resolution by Secretariat"

# --- Weekly Packet Schemas ---

class WeeklyPacketBase(SchemaBase):
    twg_id: uuid.UUID
    week_start_date: datetime
    proposed_sessions: List[dict] = []
    dependencies: List[dict] = []
    accomplishments: List[str] = []
    risks_and_blockers: List[dict] = []
    status: str = "draft"

class WeeklyPacketCreate(WeeklyPacketBase):
    pass

class WeeklyPacketRead(WeeklyPacketBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    twg: Optional["TWGBase"] = None

# Resolve forward references
TWGRead.model_rebuild()

# --- Settings Schemas ---

class SystemSettingsBase(SchemaBase):
    enable_google_calendar: bool = False
    enable_zoom: bool = False
    enable_teams: bool = False
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    smtp_config: Optional[dict] = None

class SystemSettingsUpdate(SystemSettingsBase):
    # Secrets field are optional writes
    google_credentials_json: Optional[str] = None 
    zoom_credentials_json: Optional[str] = None
    teams_credentials_json: Optional[str] = None

class SystemSettingsRead(SystemSettingsBase):
    id: uuid.UUID
    updated_at: datetime
    # Do NOT return full credentials in read schema for security, maybe just a boolean "is_configured"
    has_google_creds: bool = False
    has_zoom_creds: bool = False
    has_teams_creds: bool = False

    @staticmethod
    def from_orm_custom(obj):
        """Custom converter to hide secrets"""
        schema = SystemSettingsRead.model_validate(obj)
        schema.has_google_creds = bool(obj.google_credentials_json)
        schema.has_zoom_creds = bool(obj.zoom_credentials_json)
        schema.has_teams_creds = bool(obj.teams_credentials_json)
        return schema

class TwgSettingsBase(SchemaBase):
    meeting_cadence: Optional[str] = None
    custom_templates: Optional[dict] = None
    notification_preferences: Optional[dict] = None

class TwgSettingsUpdate(TwgSettingsBase):
    pass

class TwgSettingsRead(TwgSettingsBase):
    id: uuid.UUID
    twg_id: uuid.UUID
    updated_at: datetime

