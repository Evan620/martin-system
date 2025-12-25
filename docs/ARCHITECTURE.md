# System Architecture

## Overview

The ECOWAS Summit TWG Support System uses a federated multi-agent architecture with a supervisor-worker model to coordinate six Technical Working Groups through AI-powered automation.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  React SPA   │  │  Redux Store │  │  WebSocket   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                         REST API / WebSocket
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         Backend Layer (FastAPI)                  │
│  ┌──────────────────────────────────────────────────────────────┤
│  │                   API Gateway & Auth                         │
│  ├──────────────────────────────────────────────────────────────┤
│  │              Agent Orchestration (LangGraph)                 │
│  │  ┌──────────────┐                                            │
│  │  │  Supervisor  │────────────────────┐                       │
│  │  │    Agent     │                    │                       │
│  │  └──────────────┘                    │                       │
│  │         │                            │                       │
│  │    ┌────┴────┐                       ▼                       │
│  │    │ Worker  │          ┌────────────────────┐              │
│  │    │ Agents  │          │   Shared Tools     │              │
│  │    │   (6)   │◄─────────│  - Email           │              │
│  │    └─────────┘          │  - Calendar        │              │
│  │                         │  - Documents       │              │
│  │                         │  - Knowledge Base  │              │
│  │                         └────────────────────┘              │
│  └──────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────┐
    │ PostgreSQL  │  │   ChromaDB   │  │  Redis   │
    │ (Relational)│  │   (Vector)   │  │ (Cache)  │
    └─────────────┘  └──────────────┘  └──────────┘
```

## Component Details

### 1. Frontend Layer

**Technology**: React 18 + TypeScript + Vite

**Responsibilities**:
- User interface rendering
- State management (Redux Toolkit)
- API communication (Axios)
- Real-time updates (WebSocket)

**Key Modules**:
- **Components**: Reusable UI elements
- **Pages**: Route-level views
- **Features**: Redux slices for state
- **Services**: API client layer

### 2. Backend Layer

**Technology**: FastAPI + Python 3.11

**Responsibilities**:
- REST API endpoints
- Authentication & authorization
- Agent orchestration
- Business logic execution

**Sub-layers**:

#### a) API Gateway
- Request validation
- JWT authentication
- Rate limiting
- CORS handling
- Request/response transformation

#### b) Agent Orchestration Layer

**Technology**: LangGraph + LangChain

The heart of the system - a multi-agent coordinator:

**Supervisor Agent**:
- Routes requests to appropriate TWG agents
- Synthesizes cross-TWG outputs
- Detects and resolves conflicts
- Maintains global context

**TWG Worker Agents (6)**:
1. Energy & Infrastructure Agent
2. Agriculture & Food Systems Agent
3. Critical Minerals Agent
4. Digital Economy Agent
5. Protocol & Logistics Agent
6. Resource Mobilization Agent

Each agent:
- Has domain-specific knowledge
- Access to shared tools
- Isolated context for security
- Logging and audit trail

**Agent Communication Pattern**:
```
User Request
     │
     ▼
Supervisor Agent (routes based on TWG)
     │
     ├─► Energy Agent ──┐
     ├─► Agriculture ───┤
     ├─► Minerals ──────┤
     ├─► Digital ───────┼──► Synthesis ──► Response
     ├─► Protocol ──────┤
     └─► Resource ──────┘
```

#### c) Tools Layer

Shared tools available to all agents:

- **Email Tools**: SMTP/Gmail API integration
- **Calendar Tools**: Google/Microsoft Calendar APIs
- **Document Tools**: Generation, templating, PDF conversion
- **Meeting Tools**: Scheduling, transcription, minutes
- **Knowledge Tools**: RAG retrieval from vector DB
- **Project Tools**: Scoring, pipeline management
- **Notification Tools**: Real-time alerts

#### d) Services Layer

External integrations:
- **LLM Service**: OpenAI/Anthropic API client
- **Email Service**: Email provider abstraction
- **Calendar Service**: Calendar provider abstraction
- **Storage Service**: S3/Local file storage
- **Auth Service**: JWT token management

#### e) Core Layer

Business logic:
- **Orchestrator**: Workflow coordination
- **Knowledge Base**: Vector DB integration
- **Templates**: Email/document templates
- **Scheduler**: Background task management (Celery)

### 3. Data Layer

#### PostgreSQL (Relational Database)
Stores structured data:
- Users and roles
- TWG metadata
- Meetings and agendas
- Action items
- Projects
- Documents metadata

**Schema Design**:
```
users ─────┐
           ├──► twgs ──► meetings ──► action_items
           │                 │
           └──► projects     └──► documents
```

#### ChromaDB (Vector Database)
Stores unstructured knowledge:
- Summit concept notes
- Policy documents
- Meeting transcripts
- Reference materials

**Purpose**: Retrieval-Augmented Generation (RAG) for agent context

#### Redis (Cache & Queue)
- Session storage
- API response caching
- Celery task queue
- Real-time data (WebSocket state)

## Data Flow

### Example: Meeting Scheduling Workflow

```
1. User requests meeting via UI
   │
   ▼
2. Frontend calls POST /api/meetings
   │
   ▼
3. API validates request, checks auth
   │
   ▼
4. Routes to appropriate TWG agent
   │
   ▼
5. Agent uses tools:
   - Calendar tool: Check availability
   - Email tool: Draft invitation
   - Document tool: Generate agenda
   │
   ▼
6. Agent stores meeting in DB
   │
   ▼
7. Background task sends emails (Celery)
   │
   ▼
8. WebSocket notifies all participants
   │
   ▼
9. Response returned to user
```

## Security Architecture

### Authentication Flow

```
User Login ──► FastAPI ──► Verify Credentials
                  │
                  ▼
            Generate JWT Token
                  │
                  ▼
         Return Access + Refresh Tokens
                  │
     ┌────────────┴────────────┐
     ▼                         ▼
Access Token              Refresh Token
(30 min expiry)          (7 day expiry)
```

### Authorization

Role-Based Access Control (RBAC):

**Roles**:
- **Admin**: Full system access
- **TWG Facilitator**: Manage specific TWG
- **Member**: Read-only for assigned TWG

**Permission Matrix**:
```
Action               Admin  Facilitator  Member
─────────────────────────────────────────────
Create TWG            ✓        ✗         ✗
Edit TWG Metadata     ✓        ✓         ✗
Schedule Meeting      ✓        ✓         ✗
View Meeting          ✓        ✓         ✓
Chat with Agent       ✓        ✓         ✗
Approve Documents     ✓        ✓         ✗
View Documents        ✓        ✓         ✓
Manage Projects       ✓        ✓*        ✗
```
*Resource Mobilization only

### Data Security

- **At Rest**: PostgreSQL encryption
- **In Transit**: HTTPS/TLS
- **Secrets**: Environment variables, never in code
- **API Keys**: Stored encrypted in DB
- **Input Validation**: Pydantic schemas

## Scalability Considerations

### Horizontal Scaling

**Stateless Design**:
- API servers can scale horizontally
- Session state in Redis (shared)
- File storage in S3 (shared)

**Load Balancing**:
```
             Load Balancer
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
   API 1       API 2       API 3
      │           │           │
      └───────────┼───────────┘
                  │
          Shared Resources
      (PostgreSQL, Redis, S3)
```

### Caching Strategy

**Levels**:
1. **Browser Cache**: Static assets
2. **CDN Cache**: Public resources
3. **Redis Cache**: API responses (60s TTL)
4. **Application Cache**: In-memory for hot data

### Background Processing

**Celery Workers**:
- Email sending
- Document generation
- Meeting reminders
- Project scoring
- Report generation

**Celery Beat**:
- Scheduled meeting reminders
- Daily summaries
- Deadline notifications

## Monitoring & Observability

### Logging

**Structured Logging** (JSON format):
```json
{
  "timestamp": "2026-01-15T10:30:00Z",
  "level": "INFO",
  "service": "backend",
  "agent": "energy_agent",
  "action": "schedule_meeting",
  "user_id": "123",
  "twg_id": "energy",
  "duration_ms": 234
}
```

**Log Levels**:
- ERROR: System failures
- WARN: Unexpected but handled
- INFO: Normal operations
- DEBUG: Detailed diagnostics

### Metrics

Key metrics to track:
- API response times
- Agent execution duration
- Database query performance
- Cache hit rates
- Background task queue length

### Health Checks

**Endpoints**:
- `/health` - Overall system health
- `/health/db` - Database connectivity
- `/health/redis` - Redis connectivity
- `/health/chroma` - Vector DB connectivity

## Deployment Architecture

### Docker Compose (Development)

```yaml
services:
  - frontend (Vite dev server)
  - backend (FastAPI with reload)
  - postgres
  - redis
  - chromadb
  - celery_worker
  - celery_beat
```

### Production (Kubernetes/Cloud)

```
          ┌─── Ingress ───┐
          │               │
    ┌─────▼────┐   ┌──────▼──────┐
    │ Frontend │   │   Backend   │
    │  (nginx) │   │   (FastAPI) │
    └──────────┘   └──────┬──────┘
                          │
    ┌─────────────────────┼─────────────────┐
    │                     │                 │
┌───▼────┐        ┌───────▼──────┐   ┌──────▼────┐
│ Postgres│       │    Redis     │   │  ChromaDB │
│  (RDS)  │       │ (ElastiCache)│   │  (Pod)    │
└─────────┘       └──────────────┘   └───────────┘
```

## Technology Choices & Rationale

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Frontend Framework | React + TypeScript | Industry standard, large ecosystem, type safety |
| Backend Framework | FastAPI | Async support, auto docs, Pydantic validation |
| Agent Framework | LangGraph | Purpose-built for multi-agent systems, flexible |
| Database | PostgreSQL | Reliable, ACID, JSON support, full-text search |
| Vector DB | ChromaDB | Simple, embeddable, good for RAG |
| Cache/Queue | Redis | Fast, versatile, Celery integration |
| LLM | OpenAI/Anthropic | Best performance for complex reasoning |

## Future Enhancements

1. **Multi-language Support**: i18n for French, Portuguese
2. **Advanced Analytics**: Dashboard with charts, trends
3. **Mobile App**: React Native companion app
4. **Offline Mode**: PWA with service workers
5. **Voice Integration**: Meeting transcription via Whisper
6. **Fine-tuned Models**: Custom models for domain-specific tasks
7. **Blockchain Integration**: Immutable audit trail for decisions

## References

- FastAPI Documentation
- LangChain/LangGraph Documentation
- React Documentation
- PostgreSQL Documentation
- Redis Documentation
