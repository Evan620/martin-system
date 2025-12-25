# ECOWAS Summit TWG Support System

AI-Powered Support System for ECOWAS Summit Technical Working Groups (TWGs) - An intelligent multi-agent platform for coordinating summit operations across multiple technical working groups.

## Overview

This system provides automated support for managing six Technical Working Groups (TWGs) for the ECOWAS Economic Integration & Investment Summit 2026:

1. **Energy & Infrastructure** - Regional power integration and renewable energy initiatives
2. **Agriculture & Food Systems** - Food security and agribusiness development
3. **Critical Minerals & Industrialization** - Mining value chains and industrial development
4. **Digital Economy & Transformation** - Digital infrastructure and AI governance
5. **Protocol & Logistics** - Event planning and operational coordination
6. **Resource Mobilization** - Investment pipeline and deal room management

## Architecture

The system uses a **federated multi-agent architecture** built with LangGraph, where:

- **Supervisor Agent**: Orchestrates all TWG agents, ensures consistency, and synthesizes cross-TWG outputs
- **TWG Agents** (6): Each agent specializes in its domain, handling meeting coordination, document drafting, and project curation

### Tech Stack

**Backend:**
- Python 3.11
- FastAPI (async web framework)
- LangGraph & LangChain (agent orchestration)
- ChromaDB (vector database for RAG)
- SQLAlchemy (ORM)
- PostgreSQL (relational database)

**Frontend:**
- React 18 with TypeScript
- Vite (build tool)
- Redux Toolkit (state management)
- TailwindCSS (styling)
- Axios (HTTP client)

**Infrastructure:**
- Docker & Docker Compose
- Redis (caching/queues)
- Nginx (frontend serving)

## Features

### Automated Workflows
- Meeting scheduling and calendar integration
- Automated email invitations with .ics attachments
- Real-time meeting transcription and minute-taking
- Document generation (agendas, minutes, policy papers)
- Action item tracking and reminders

### Portal Capabilities
- Role-based access control (Admins, TWG Facilitators, Members)
- TWG-specific dashboards
- Interactive agent chat interface
- Document repository with version control
- Project pipeline visualization (Deal Room)
- Real-time notifications

### AI Agent Tools
- Email automation (SMTP/Gmail API)
- Calendar integration (Google Calendar/Outlook)
- Document generation and PDF conversion
- Knowledge base retrieval (RAG)
- Project scoring and matching
- Meeting transcription and summarization

## Project Structure

```
martins-system/
├── backend/          # FastAPI + LangGraph backend
│   ├── app/
│   │   ├── agents/   # AI agents (supervisor + 6 TWG agents)
│   │   ├── tools/    # Agent tools (email, calendar, documents, etc.)
│   │   ├── api/      # REST API endpoints
│   │   ├── models/   # Database models
│   │   ├── core/     # Business logic
│   │   └── services/ # External integrations
│   └── tests/
├── frontend/         # React + TypeScript frontend
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── features/
│       └── services/
├── docs/            # Documentation
└── docker-compose.yml
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional)
- PostgreSQL 15+ (if not using Docker)

### Quick Start with Docker

```bash
# Clone the repository
git clone <repository-url>
cd martins-system

# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## Configuration

### Environment Variables

See `.env.example`, `backend/.env.example`, and `frontend/.env.example` for all required environment variables.

Key configurations:
- Database connection strings
- LLM API keys (OpenAI/Anthropic)
- Email service credentials (SMTP/Gmail API)
- Calendar API credentials (Google/Microsoft)
- JWT secrets for authentication
- Storage configuration (S3/local)

## API Documentation

Once the backend is running, interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Documentation

Detailed documentation is available in the `docs/` directory:

- [API.md](docs/API.md) - REST API endpoint reference
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture and design
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guides
- [USER_GUIDE.md](docs/USER_GUIDE.md) - User manual for portal

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting
cd backend
black app/
flake8 app/

# Frontend linting
cd frontend
npm run lint
```

## Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions for various environments (AWS, Azure, GCP, on-premises).

## Security

- All API endpoints require JWT authentication
- Role-based access control (RBAC) enforced at API and UI levels
- Sensitive data encrypted at rest and in transit
- Environment variables for all secrets
- Input validation and sanitization
- Rate limiting on API endpoints

## Contributing

This is an internal project for the ECOWAS Summit. For questions or support, contact the development team.

## License

Proprietary - ECOWAS Summit 2026

## Support

For technical support or questions:
- Technical Lead: [Contact Information]
- Project Manager: [Contact Information]
- Documentation: [Internal Wiki/Confluence]

---

**Status**: Initial Setup Phase
**Version**: 0.1.0
**Last Updated**: December 2025
