# ECOWAS Summit TWG System - Backend

FastAPI backend with LangGraph multi-agent system for managing Technical Working Groups.

## Architecture

The backend follows a modular architecture:

```
app/
├── agents/          # LangGraph AI agents (supervisor + 6 TWG agents)
├── tools/           # Agent tools (email, calendar, documents, etc.)
├── api/             # REST API endpoints and middleware
├── models/          # SQLAlchemy database models
├── schemas/         # Pydantic schemas for validation
├── services/        # External integrations (email, LLM, storage)
├── core/            # Business logic (orchestrator, knowledge base)
└── utils/           # Utility functions
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- ChromaDB (for vector storage)

### Installation

1. Create and activate virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Setup environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize database:
```bash
# Run migrations
alembic upgrade head

# Optional: Seed initial data
python scripts/init_db.py
python scripts/seed_data.py
```

### Running the Server

Development mode with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Production mode:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, access interactive API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run all tests:
```bash
pytest
```

With coverage:
```bash
pytest --cov=app --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_agents/test_supervisor.py
```

## Code Quality

Format code:
```bash
black app/
```

Lint code:
```bash
flake8 app/
mypy app/
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## Background Tasks

Start Celery worker:
```bash
celery -A app.core.scheduler worker --loglevel=info
```

Start Celery beat (scheduler):
```bash
celery -A app.core.scheduler beat --loglevel=info
```

## Agent System

### Supervisor Agent
Central orchestrator that:
- Routes requests to appropriate TWG agents
- Synthesizes outputs across agents
- Detects and resolves conflicts
- Maintains global state

### TWG Agents (6)
Each specialized for their domain:
1. **Energy Agent** - Energy & Infrastructure
2. **Agriculture Agent** - Agriculture & Food Systems
3. **Minerals Agent** - Critical Minerals & Industrialization
4. **Digital Agent** - Digital Economy & Transformation
5. **Protocol Agent** - Protocol & Logistics
6. **Resource Mobilization Agent** - Investment pipeline

### Agent Tools
- **Email Tools**: Send emails, generate invitations
- **Calendar Tools**: Schedule meetings, check availability
- **Document Tools**: Generate agendas, minutes, policy papers
- **Meeting Tools**: Create records, extract action items
- **Knowledge Tools**: RAG retrieval from vector DB
- **Project Tools**: Score projects, manage pipeline
- **Notification Tools**: Send alerts and reminders

## Configuration

Key environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: OpenAI API key for LLM
- `SMTP_*`: Email configuration
- `GOOGLE_CALENDAR_*`: Calendar API credentials
- `SECRET_KEY`: JWT signing key

See `.env.example` for full list.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application
│   ├── config.py                # Configuration
│   ├── agents/                  # AI Agents
│   │   ├── base_agent.py
│   │   ├── supervisor.py
│   │   ├── energy_agent.py
│   │   ├── agriculture_agent.py
│   │   ├── minerals_agent.py
│   │   ├── digital_agent.py
│   │   ├── protocol_agent.py
│   │   ├── resource_mobilization_agent.py
│   │   └── graph_builder.py
│   ├── tools/                   # Agent Tools
│   │   ├── email_tools.py
│   │   ├── calendar_tools.py
│   │   ├── document_tools.py
│   │   ├── meeting_tools.py
│   │   ├── knowledge_tools.py
│   │   ├── project_tools.py
│   │   └── notification_tools.py
│   ├── api/                     # API Layer
│   │   ├── deps.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── twgs.py
│   │   │   ├── meetings.py
│   │   │   ├── documents.py
│   │   │   ├── projects.py
│   │   │   └── agents.py
│   │   └── middleware/
│   │       └── auth.py
│   ├── models/                  # Database Models
│   │   ├── database.py
│   │   ├── user.py
│   │   ├── twg.py
│   │   ├── meeting.py
│   │   ├── action_item.py
│   │   ├── document.py
│   │   └── project.py
│   ├── schemas/                 # Pydantic Schemas
│   ├── services/                # External Services
│   ├── core/                    # Core Logic
│   └── utils/                   # Utilities
├── tests/
├── scripts/
├── storage/                     # Local file storage
├── logs/                        # Application logs
├── requirements.txt
└── README.md
```

## Common Tasks

### Adding a New Agent

1. Create agent file in `app/agents/new_agent.py`
2. Extend `BaseAgent` class
3. Define agent persona and tools
4. Register in `graph_builder.py`
5. Add tests in `tests/test_agents/`

### Adding a New Tool

1. Create tool file in `app/tools/new_tool.py`
2. Implement tool functions
3. Add tool to appropriate agent's tool list
4. Write tests

### Adding a New API Endpoint

1. Define schema in `app/schemas/`
2. Create route in `app/api/routes/`
3. Register router in `app/main.py`
4. Add tests in `tests/test_api/`

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql postgresql://ecowas_user:password@localhost:5432/ecowas_summit_db
```

### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

### ChromaDB Issues
```bash
# Verify ChromaDB is accessible
curl http://localhost:8001/api/v1/heartbeat
```

## Contributing

1. Create feature branch from `main`
2. Write tests for new features
3. Ensure all tests pass
4. Format code with Black
5. Submit pull request

## License

Proprietary - ECOWAS Summit 2026
