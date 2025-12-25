# Project Structure - ECOWAS Summit TWG System

## Complete Directory Structure

```
Martins System/
│
├── README.md                          # Project overview and quick start
├── .gitignore                         # Git ignore rules
├── .env.example                       # Root environment template
├── docker-compose.yml                 # Docker multi-container configuration
├── PROJECT_STRUCTURE.md               # This file
│
├── backend/                           # Python FastAPI Backend
│   ├── README.md                      # Backend documentation
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Backend environment template
│   ├── Dockerfile                     # Backend container config
│   │
│   ├── venv/                          # Python virtual environment (✓ Created)
│   │
│   ├── app/                           # Main application package
│   │   ├── __init__.py
│   │   ├── main.py                    # [TODO] FastAPI app entry point
│   │   ├── config.py                  # [TODO] Configuration management
│   │   │
│   │   ├── agents/                    # LangGraph AI Agents (✓ Structure created)
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py          # [TODO] Base agent class
│   │   │   ├── supervisor.py          # [TODO] Supervisor/orchestrator
│   │   │   ├── energy_agent.py        # [TODO] Energy TWG agent
│   │   │   ├── agriculture_agent.py   # [TODO] Agriculture TWG agent
│   │   │   ├── minerals_agent.py      # [TODO] Minerals TWG agent
│   │   │   ├── digital_agent.py       # [TODO] Digital Economy agent
│   │   │   ├── protocol_agent.py      # [TODO] Protocol & Logistics agent
│   │   │   ├── resource_mobilization_agent.py  # [TODO] Resource agent
│   │   │   └── graph_builder.py       # [TODO] LangGraph construction
│   │   │
│   │   ├── tools/                     # Agent Tools (✓ Structure created)
│   │   │   ├── __init__.py
│   │   │   ├── email_tools.py         # [TODO] Email sending, formatting
│   │   │   ├── calendar_tools.py      # [TODO] Calendar integration
│   │   │   ├── document_tools.py      # [TODO] Document generation
│   │   │   ├── meeting_tools.py       # [TODO] Meeting management
│   │   │   ├── knowledge_tools.py     # [TODO] RAG retrieval
│   │   │   ├── project_tools.py       # [TODO] Project scoring
│   │   │   └── notification_tools.py  # [TODO] Notifications
│   │   │
│   │   ├── api/                       # API Layer (✓ Structure created)
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # [TODO] Shared dependencies
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py            # [TODO] Authentication
│   │   │   │   ├── twgs.py            # [TODO] TWG management
│   │   │   │   ├── meetings.py        # [TODO] Meeting endpoints
│   │   │   │   ├── documents.py       # [TODO] Document endpoints
│   │   │   │   ├── projects.py        # [TODO] Project endpoints
│   │   │   │   └── agents.py          # [TODO] Agent interaction
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       └── auth.py            # [TODO] Auth middleware
│   │   │
│   │   ├── models/                    # Database Models (✓ Structure created)
│   │   │   ├── __init__.py
│   │   │   ├── database.py            # [TODO] DB connection
│   │   │   ├── user.py                # [TODO] User model
│   │   │   ├── twg.py                 # [TODO] TWG model
│   │   │   ├── meeting.py             # [TODO] Meeting model
│   │   │   ├── action_item.py         # [TODO] Action item model
│   │   │   ├── document.py            # [TODO] Document model
│   │   │   └── project.py             # [TODO] Project model
│   │   │
│   │   ├── schemas/                   # Pydantic Schemas (✓ Structure created)
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # [TODO] User schemas
│   │   │   ├── twg.py                 # [TODO] TWG schemas
│   │   │   ├── meeting.py             # [TODO] Meeting schemas
│   │   │   ├── document.py            # [TODO] Document schemas
│   │   │   └── project.py             # [TODO] Project schemas
│   │   │
│   │   ├── services/                  # External Services (✓ Structure created)
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py        # [TODO] JWT authentication
│   │   │   ├── email_service.py       # [TODO] Email provider
│   │   │   ├── calendar_service.py    # [TODO] Calendar provider
│   │   │   ├── storage_service.py     # [TODO] File storage
│   │   │   └── llm_service.py         # [TODO] LLM API client
│   │   │
│   │   ├── core/                      # Core Logic (✓ Structure created)
│   │   │   ├── __init__.py
│   │   │   ├── knowledge_base.py      # [TODO] ChromaDB integration
│   │   │   ├── templates.py           # [TODO] Document templates
│   │   │   ├── scheduler.py           # [TODO] Background tasks
│   │   │   └── orchestrator.py        # [TODO] Agent coordination
│   │   │
│   │   └── utils/                     # Utilities (✓ Structure created)
│   │       ├── __init__.py
│   │       ├── security.py            # [TODO] Security utilities
│   │       ├── validators.py          # [TODO] Validation functions
│   │       └── helpers.py             # [TODO] Helper functions
│   │
│   ├── tests/                         # Tests (✓ Structure created)
│   │   ├── __init__.py
│   │   ├── conftest.py                # [TODO] Test configuration
│   │   ├── test_agents/               # [TODO] Agent tests
│   │   ├── test_tools/                # [TODO] Tool tests
│   │   └── test_api/                  # [TODO] API tests
│   │
│   ├── scripts/                       # Utility Scripts (✓ Structure created)
│   │   ├── init_db.py                 # [TODO] Database initialization
│   │   └── seed_data.py               # [TODO] Seed initial data
│   │
│   ├── storage/                       # Local File Storage (✓ Created)
│   ├── logs/                          # Application Logs (✓ Created)
│   ├── credentials/                   # API Credentials (✓ Created)
│   └── chroma_data/                   # ChromaDB Data (✓ Created)
│
├── frontend/                          # React TypeScript Frontend
│   ├── README.md                      # Frontend documentation (✓ Created)
│   ├── package.json                   # NPM dependencies (✓ Created)
│   ├── tsconfig.json                  # TypeScript config (✓ Created)
│   ├── tsconfig.node.json             # Node TypeScript config (✓ Created)
│   ├── vite.config.ts                 # Vite configuration (✓ Created)
│   ├── .env.example                   # Frontend environment (✓ Created)
│   ├── Dockerfile                     # Frontend container (✓ Created)
│   ├── nginx.conf                     # Nginx configuration (✓ Created)
│   │
│   ├── public/                        # Static Assets (✓ Structure created)
│   │   └── assets/
│   │
│   ├── src/                           # Source Code (✓ Structure created)
│   │   ├── main.tsx                   # [TODO] App entry point
│   │   ├── App.tsx                    # [TODO] Main app component
│   │   ├── vite-env.d.ts              # [TODO] Vite type declarations
│   │   │
│   │   ├── components/                # UI Components
│   │   │   ├── common/                # [TODO] Generic components
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   └── Loader.tsx
│   │   │   ├── layout/                # [TODO] Layout components
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Footer.tsx
│   │   │   ├── twg/                   # [TODO] TWG components
│   │   │   │   ├── TWGCard.tsx
│   │   │   │   ├── TWGDashboard.tsx
│   │   │   │   └── TWGSelector.tsx
│   │   │   ├── meetings/              # [TODO] Meeting components
│   │   │   │   ├── MeetingCard.tsx
│   │   │   │   ├── MeetingCalendar.tsx
│   │   │   │   └── MeetingTimeline.tsx
│   │   │   ├── documents/             # [TODO] Document components
│   │   │   │   ├── DocumentList.tsx
│   │   │   │   ├── DocumentViewer.tsx
│   │   │   │   └── DocumentUpload.tsx
│   │   │   ├── agents/                # [TODO] Agent components
│   │   │   │   ├── AgentChat.tsx
│   │   │   │   └── AgentStatus.tsx
│   │   │   └── projects/              # [TODO] Project components
│   │   │       ├── ProjectCard.tsx
│   │   │       ├── ProjectPipeline.tsx
│   │   │       └── ProjectScoring.tsx
│   │   │
│   │   ├── pages/                     # Page Components
│   │   │   ├── Login.tsx              # [TODO] Login page
│   │   │   ├── Dashboard.tsx          # [TODO] Main dashboard
│   │   │   ├── TWGWorkspace.tsx       # [TODO] TWG workspace
│   │   │   ├── MeetingsPage.tsx       # [TODO] Meetings page
│   │   │   ├── DocumentsPage.tsx      # [TODO] Documents page
│   │   │   ├── ProjectsPage.tsx       # [TODO] Projects page
│   │   │   └── SettingsPage.tsx       # [TODO] Settings page
│   │   │
│   │   ├── features/                  # Redux Features
│   │   │   ├── auth/                  # [TODO] Auth state
│   │   │   │   ├── authSlice.ts
│   │   │   │   └── authAPI.ts
│   │   │   ├── twg/                   # [TODO] TWG state
│   │   │   │   ├── twgSlice.ts
│   │   │   │   └── twgAPI.ts
│   │   │   └── meetings/              # [TODO] Meetings state
│   │   │       ├── meetingsSlice.ts
│   │   │       └── meetingsAPI.ts
│   │   │
│   │   ├── hooks/                     # Custom Hooks
│   │   │   ├── useAuth.ts             # [TODO] Auth hook
│   │   │   ├── useAgent.ts            # [TODO] Agent hook
│   │   │   └── useWebSocket.ts        # [TODO] WebSocket hook
│   │   │
│   │   ├── services/                  # API Services
│   │   │   ├── api.ts                 # [TODO] Axios instance
│   │   │   ├── authService.ts         # [TODO] Auth API
│   │   │   ├── twgService.ts          # [TODO] TWG API
│   │   │   ├── meetingService.ts      # [TODO] Meeting API
│   │   │   └── agentService.ts        # [TODO] Agent API
│   │   │
│   │   ├── store/                     # Redux Store
│   │   │   ├── store.ts               # [TODO] Store config
│   │   │   └── rootReducer.ts         # [TODO] Root reducer
│   │   │
│   │   ├── types/                     # TypeScript Types
│   │   │   ├── index.ts               # [TODO] Main exports
│   │   │   ├── user.ts                # [TODO] User types
│   │   │   ├── twg.ts                 # [TODO] TWG types
│   │   │   ├── meeting.ts             # [TODO] Meeting types
│   │   │   └── agent.ts               # [TODO] Agent types
│   │   │
│   │   ├── utils/                     # Utilities
│   │   │   ├── constants.ts           # [TODO] Constants
│   │   │   ├── helpers.ts             # [TODO] Helper functions
│   │   │   └── formatters.ts          # [TODO] Data formatters
│   │   │
│   │   └── styles/                    # Global Styles
│   │       ├── index.css              # [TODO] Main stylesheet
│   │       └── theme.ts               # [TODO] Theme config
│   │
│   └── tests/                         # Frontend Tests
│       └── setup.ts                   # [TODO] Test setup
│
└── docs/                              # Documentation (✓ All created)
    ├── API.md                         # API reference (✓ Created)
    ├── ARCHITECTURE.md                # System architecture (✓ Created)
    ├── DEPLOYMENT.md                  # Deployment guide (✓ Created)
    └── USER_GUIDE.md                  # User manual (✓ Created)
```

## Setup Completion Status

### ✅ Completed

1. **Root Configuration**
   - [✓] .gitignore
   - [✓] README.md
   - [✓] .env.example
   - [✓] docker-compose.yml
   - [✓] PROJECT_STRUCTURE.md

2. **Backend Structure**
   - [✓] Directory structure created
   - [✓] Python virtual environment (venv)
   - [✓] requirements.txt
   - [✓] .env.example
   - [✓] Dockerfile
   - [✓] README.md
   - [✓] All module __init__.py files

3. **Frontend Structure**
   - [✓] Directory structure created
   - [✓] package.json
   - [✓] tsconfig.json
   - [✓] vite.config.ts
   - [✓] .env.example
   - [✓] Dockerfile
   - [✓] nginx.conf
   - [✓] README.md

4. **Documentation**
   - [✓] API.md
   - [✓] ARCHITECTURE.md
   - [✓] DEPLOYMENT.md
   - [✓] USER_GUIDE.md

### 📋 Next Steps (Implementation Phase)

#### Phase 1: Core Backend Setup
1. Create FastAPI application (`app/main.py`)
2. Setup database connection and models
3. Implement authentication system
4. Create base API endpoints

#### Phase 2: Agent System
1. Implement base agent class
2. Create supervisor agent
3. Build individual TWG agents (start with 1-2)
4. Develop agent tools

#### Phase 3: Frontend Foundation
1. Create main React app structure
2. Setup Redux store
3. Implement authentication UI
4. Build base layout components

#### Phase 4: Integration
1. Connect frontend to backend API
2. Implement agent chat interface
3. Build meeting management UI
4. Create document repository

#### Phase 5: Testing & Refinement
1. Write tests for critical paths
2. Load testing
3. Security audit
4. User acceptance testing

## Quick Start Commands

### Backend

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (when ready to code)
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your values

# Run development server (once app/main.py is created)
uvicorn app.main:app --reload
```

### Frontend

```bash
# Navigate to frontend
cd frontend

# Install dependencies (when ready to code)
npm install

# Create .env from template
cp .env.example .env
# Edit .env with your values

# Run development server (once src files are created)
npm run dev
```

### Docker (Full Stack)

```bash
# From project root
cp .env.example .env
# Edit .env with your values

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Key Technologies

### Backend
- Python 3.11+
- FastAPI (web framework)
- LangGraph + LangChain (agents)
- PostgreSQL (database)
- ChromaDB (vector database)
- Redis (cache/queue)
- Celery (background tasks)

### Frontend
- React 18
- TypeScript
- Vite (build tool)
- Redux Toolkit (state)
- TailwindCSS (styling)
- Axios (HTTP)

### Infrastructure
- Docker & Docker Compose
- Nginx (reverse proxy)
- PostgreSQL 15
- Redis 7
- ChromaDB

## File Naming Conventions

### Backend (Python)
- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case()`
- **Constants**: `UPPER_SNAKE_CASE`

### Frontend (TypeScript/React)
- **Components**: `PascalCase.tsx`
- **Hooks**: `useCamelCase.ts`
- **Utils**: `camelCase.ts`
- **Types**: `PascalCase` interfaces

## Environment Variables

See individual `.env.example` files for complete lists:
- Root: General configuration
- Backend: API keys, database URLs, secrets
- Frontend: API URLs, feature flags

## Development Workflow

1. **Create Feature Branch**: `git checkout -b feature/agent-email-tools`
2. **Write Code**: Follow structure above
3. **Test Locally**: Run tests, manual testing
4. **Commit**: Descriptive commit messages
5. **Push & PR**: Create pull request for review

## Getting Help

- **Documentation**: Check `/docs` directory
- **README files**: Each module has its own README
- **Code Comments**: Inline documentation
- **API Docs**: http://localhost:8000/docs (once backend running)

## License

Proprietary - ECOWAS Summit 2026

---

**Project Status**: ✅ Structure Complete - Ready for Implementation
**Created**: December 2025
**Version**: 0.1.0
