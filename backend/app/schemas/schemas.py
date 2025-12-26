from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Any
import uuid
import enum

# --- Enums (mirrored from models) ---

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TWG_FACILITATOR = "twg_facilitator"
    TWG_MEMBER = "twg_member"
    SECRETARIAT_LEAD = "secretariat_lead"

class TWGPillar(str, enum.Enum):
    ENERGY = "energy"
    AGRIBUSINESS = "agribusiness"
    MINERALS = "minerals"
    DIGITAL = "digital"
    LOGISTICS = "logistics"
    RESOURCE_MOBILIZATION = "resource_mobilization"

class MeetingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

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

class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

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

class TWGRead(TWGBase):
    id: uuid.UUID

# --- Meeting Schemas ---

class MeetingBase(SchemaBase):
    twg_id: uuid.UUID
    title: str
    scheduled_at: datetime
    duration_minutes: int = 60
    location: Optional[str] = None
    status: MeetingStatus = MeetingStatus.SCHEDULED
    meeting_type: str = "virtual"

class MeetingCreate(MeetingBase):
    pass

class MeetingRead(MeetingBase):
    id: uuid.UUID

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

# --- Project Schemas ---

class ProjectBase(SchemaBase):
    twg_id: uuid.UUID
    name: str
    description: str
    investment_size: float
    currency: str = "USD"
    readiness_score: float = 0.0
    status: ProjectStatus = ProjectStatus.IDENTIFIED
    metadata_json: Optional[dict] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectRead(ProjectBase):
    id: uuid.UUID

# --- Document Schemas ---

class DocumentBase(SchemaBase):
    twg_id: Optional[uuid.UUID] = None
    file_name: str
    file_type: str
    is_confidential: bool = False
    metadata_json: Optional[dict] = None

class DocumentCreate(DocumentBase):
    file_path: str
    uploaded_by_id: uuid.UUID

class DocumentRead(DocumentBase):
    id: uuid.UUID
    file_path: str
    uploaded_by_id: uuid.UUID
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
