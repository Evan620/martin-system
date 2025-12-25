# API Documentation

## Base URL

Development: `http://localhost:8000`
Production: `https://api.ecowas-summit.org`

## Authentication

All endpoints except `/auth/login` and `/auth/register` require authentication.

### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Endpoints

### Authentication

#### POST /auth/login
Login and receive JWT tokens.

**Request**:
```json
{
  "email": "user@ecowas.int",
  "password": "password123"
}
```

**Response**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@ecowas.int",
    "role": "facilitator",
    "twg_id": "energy"
  }
}
```

#### POST /auth/refresh
Refresh access token using refresh token.

#### POST /auth/logout
Invalidate current token.

### TWGs (Technical Working Groups)

#### GET /twgs
List all TWGs.

#### GET /twgs/{twg_id}
Get specific TWG details.

#### POST /twgs
Create new TWG (Admin only).

#### PUT /twgs/{twg_id}
Update TWG metadata.

### Meetings

#### GET /meetings
List meetings (filtered by user's TWG).

#### GET /meetings/{meeting_id}
Get meeting details.

#### POST /meetings
Schedule new meeting.

**Request**:
```json
{
  "twg_id": "energy",
  "title": "Energy Integration Planning",
  "date": "2026-02-15T10:00:00Z",
  "duration_minutes": 90,
  "participants": ["email1@ecowas.int", "email2@ecowas.int"],
  "agenda_items": ["Review policy draft", "Discuss timeline"]
}
```

#### PUT /meetings/{meeting_id}
Update meeting details.

#### DELETE /meetings/{meeting_id}
Cancel meeting.

### Documents

#### GET /documents
List documents.

#### GET /documents/{document_id}
Get document metadata.

#### GET /documents/{document_id}/download
Download document file.

#### POST /documents
Upload document.

#### PUT /documents/{document_id}
Update document metadata.

### Projects

#### GET /projects
List projects in pipeline.

#### GET /projects/{project_id}
Get project details.

#### POST /projects
Submit new project.

#### PUT /projects/{project_id}/score
Update project score.

### Agents

#### POST /agents/chat
Send message to agent.

**Request**:
```json
{
  "twg_id": "energy",
  "message": "Draft agenda for next meeting",
  "context": {}
}
```

**Response**:
```json
{
  "agent": "energy_agent",
  "response": "I've drafted the agenda...",
  "actions_taken": ["created_draft"],
  "requires_approval": true
}
```

#### GET /agents/status
Get agent system status.

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "errors": [...]
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "request_id": "uuid"
}
```

## Rate Limiting

- 60 requests per minute per user
- 429 Too Many Requests returned when exceeded

## Pagination

List endpoints support pagination:

**Query Parameters**:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

**Response**:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "pages": 8
}
```

## Filtering & Sorting

**Query Parameters**:
- `sort_by`: Field to sort by
- `order`: `asc` or `desc`
- `filter[field]`: Filter by field value

Example: `/meetings?sort_by=date&order=desc&filter[twg_id]=energy`

## WebSocket

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=<access_token>')
```

### Events

**Client → Server**:
```json
{
  "type": "subscribe",
  "channel": "twg:energy"
}
```

**Server → Client**:
```json
{
  "type": "notification",
  "channel": "twg:energy",
  "data": {
    "message": "New meeting scheduled"
  }
}
```

## Postman Collection

Import the Postman collection for easy API testing:
`/docs/postman_collection.json`

For complete interactive documentation, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
