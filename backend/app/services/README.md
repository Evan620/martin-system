# Services Package

External integrations and shared services for the ECOWAS Summit TWG Support System.

## Overview

This package contains service modules that provide integrations with external systems and shared functionality across the application:

- **LLM Service** - Local Ollama integration for AI agent interactions
- **Redis Memory Service** - Persistent, distributed memory storage for agents

---

## LLM Service

### Description
Provides an interface to connect to a local Ollama instance for AI agent interactions.

### Features
- Chat with conversation history
- Temperature and token control
- Connection health checks
- Timeout management

### Usage

```python
from app.services.llm_service import get_llm_service

# Get LLM service singleton
llm = get_llm_service()

# Simple chat
response = llm.chat(
    prompt="What are the ECOWAS energy initiatives?",
    system_prompt="You are an energy expert.",
    temperature=0.7
)

# Chat with history
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
    {"role": "user", "content": "Tell me about renewable energy"}
]
response = llm.chat_with_history(messages)
```

### Configuration

Set in `.env` or environment variables:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:0.5b
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=30
```

---

## Redis Memory Service

### Description
Provides persistent, distributed memory storage for agent conversations using Redis. Enables conversation history tracking, session management, and cross-instance state sharing.

### Features

#### Core Capabilities
- ✅ **Persistent Conversation History** - Survive server restarts
- ✅ **Session-Based Tracking** - Multiple conversations per agent
- ✅ **Distributed State** - Share state across multiple instances
- ✅ **Automatic TTL Management** - Keys expire automatically
- ✅ **Multi-Agent Support** - Manage multiple agents and sessions
- ✅ **Agent State Persistence** - Save/load agent state
- ✅ **Session Metadata** - Store arbitrary session data

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              Redis Memory Service                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Conversation │  │    Agent     │  │ Session  │ │
│  │   History    │  │    State     │  │   Data   │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
│  Key Format: ecowas:{namespace}:{identifier}       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Quick Start

#### 1. Basic Setup

```python
from app.services.redis_memory import get_redis_memory

# Initialize Redis memory service
redis_memory = get_redis_memory(
    host="redis.railway.internal",
    port=6379,
    password="your-password",
    db=0
)

# Check connection
if redis_memory.health_check():
    print("Connected to Redis!")
```

#### 2. Conversation History

```python
# Save conversation history
history = [
    {"role": "user", "content": "What are ECOWAS energy initiatives?"},
    {"role": "assistant", "content": "ECOWAS has several initiatives..."}
]

redis_memory.save_conversation_history(
    agent_id="energy",
    session_id="user-123-session-1",
    history=history,
    ttl=86400  # 24 hours
)

# Retrieve history
retrieved = redis_memory.get_conversation_history("energy", "user-123-session-1")

# Append to history
new_message = {"role": "user", "content": "Tell me more"}
redis_memory.append_to_history("energy", "user-123-session-1", new_message, max_history=10)

# Clear history
redis_memory.clear_conversation_history("energy", "user-123-session-1")
```

#### 3. Agent State Management

```python
# Save agent state
state = {
    "active_agents": ["energy", "agriculture"],
    "pending_requests": 3,
    "last_delegation": "energy"
}
redis_memory.save_agent_state("supervisor", state)

# Load agent state
state = redis_memory.get_agent_state("supervisor")
```

#### 4. Session Data

```python
# Store session metadata
session_data = {
    "user_id": "user-123",
    "twg": "energy",
    "preferences": {"language": "en"}
}
redis_memory.set_session_data("session-1", "metadata", session_data)

# Retrieve session data
data = redis_memory.get_session_data("session-1", "metadata")
```

### Using RedisAgent

The `RedisAgent` class extends `BaseAgent` with Redis-backed persistence:

```python
from app.agents.redis_agent import RedisAgent

# Create Redis-enabled agent
agent = RedisAgent(
    agent_id="energy",
    session_id="user-123-session-1",
    keep_history=True,
    max_history=10,
    use_redis=True
)

# Chat (automatically saves to Redis)
response = agent.chat("What are the renewable energy targets?")

# History is automatically loaded on next instantiation
agent2 = RedisAgent(
    agent_id="energy",
    session_id="user-123-session-1",  # Same session
    keep_history=True
)
# agent2.history will contain previous conversation

# Get session info
info = agent.get_session_info()
print(f"Session: {info['session_id']}, History: {info['history_length']} messages")

# Reset conversation
agent.reset_history()
```

### Advanced Features

#### TTL Management

```python
# Save with custom TTL
redis_memory.save_conversation_history(
    "energy", "session-1", history,
    ttl=3600  # 1 hour
)

# Extend TTL (e.g., user still active)
redis_memory.extend_ttl("energy", "session-1", ttl=7200)  # 2 hours
```

#### Multi-Session Management

```python
# Get all sessions for an agent
sessions = redis_memory.get_all_sessions_for_agent("energy")
print(f"Found {len(sessions)} sessions")

# Clear all data for an agent
deleted = redis_memory.clear_all_agent_data("energy")
print(f"Deleted {deleted} keys")
```

#### Memory Statistics

```python
stats = redis_memory.get_memory_stats()
print(f"Used Memory: {stats['used_memory']}")
print(f"Total Keys: {stats['total_keys']}")
```

### Configuration

#### Environment Variables

```bash
# Redis Configuration
REDIS_HOST=redis.railway.internal
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-password
REDIS_MEMORY_TTL=86400  # 24 hours

# Agent Configuration
AGENT_USE_REDIS_MEMORY=true
AGENT_MAX_HISTORY=10
SUPERVISOR_MAX_HISTORY=20
```

#### From Config File

```python
from app.services.redis_factory import create_redis_memory_from_config

# Create from app config
redis_memory = create_redis_memory_from_config()
```

### Key Namespaces

The service uses namespaced keys for organization:

| Namespace | Format | Purpose |
|-----------|--------|---------|
| `history` | `ecowas:history:{agent_id}:{session_id}` | Conversation history |
| `state` | `ecowas:state:{agent_id}` | Agent state |
| `session` | `ecowas:session:{session_id}:{key}` | Session data |

### Best Practices

#### 1. Session Management
```python
# Use meaningful session IDs
session_id = f"user-{user_id}-{timestamp}"

# Extend TTL on user activity
redis_memory.extend_ttl(agent_id, session_id)
```

#### 2. History Limits
```python
# Prevent unbounded growth
redis_memory.append_to_history(
    agent_id, session_id, message,
    max_history=20  # Keep last 20 messages
)
```

#### 3. Cleanup
```python
# Clear old sessions periodically
for session_id in old_sessions:
    redis_memory.clear_conversation_history(agent_id, session_id)
```

#### 4. Error Handling
```python
# Always check health before critical operations
if not redis_memory.health_check():
    # Fallback to in-memory or retry
    logger.error("Redis unavailable, using fallback")
```

### Testing

#### Run Tests

```bash
# All Redis tests
pytest tests/test_redis_memory.py -v

# Specific test
pytest tests/test_redis_memory.py::test_save_and_get_conversation_history -v

# With coverage
pytest tests/test_redis_memory.py --cov=app.services.redis_memory
```

#### Quick Connection Test

```bash
python test_redis_connection.py
```

#### Run Examples

```bash
python examples/redis_memory_example.py
```

### API Reference

#### RedisMemoryService

**Constructor**
```python
RedisMemoryService(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    default_ttl: int = 86400
)
```

**Methods**

| Method | Description |
|--------|-------------|
| `save_conversation_history(agent_id, session_id, history, ttl)` | Save conversation history |
| `get_conversation_history(agent_id, session_id)` | Retrieve conversation history |
| `append_to_history(agent_id, session_id, message, max_history, ttl)` | Append message to history |
| `clear_conversation_history(agent_id, session_id)` | Clear conversation history |
| `save_agent_state(agent_id, state, ttl)` | Save agent state |
| `get_agent_state(agent_id)` | Retrieve agent state |
| `set_session_data(session_id, key, value, ttl)` | Store session data |
| `get_session_data(session_id, key)` | Retrieve session data |
| `get_all_sessions_for_agent(agent_id)` | Get all session IDs for agent |
| `extend_ttl(agent_id, session_id, ttl)` | Extend TTL for session |
| `get_memory_stats()` | Get Redis memory statistics |
| `clear_all_agent_data(agent_id)` | Clear all data for agent |
| `health_check()` | Check Redis connection health |
| `close()` | Close Redis connection |

### Troubleshooting

#### Connection Issues

```python
# Check if Redis is reachable
try:
    redis_memory = get_redis_memory()
    if redis_memory.health_check():
        print("✅ Connected")
    else:
        print("❌ Connection failed")
except Exception as e:
    print(f"Error: {e}")
```

**Common Issues:**
1. **Connection refused** - Check Redis server is running
2. **Authentication failed** - Verify password in config
3. **Network timeout** - Check firewall/network settings
4. **Database full** - Check Redis memory limits

#### Performance Tips

1. **Use appropriate TTLs** - Shorter for temporary data
2. **Batch operations** - Group related saves
3. **Limit history size** - Use `max_history` parameter
4. **Monitor memory** - Check `get_memory_stats()` regularly

### Production Considerations

#### Security
- ✅ Use strong passwords
- ✅ Enable TLS/SSL for production
- ✅ Restrict network access
- ✅ Rotate credentials regularly

#### Scaling
- ✅ Use Redis Cluster for high availability
- ✅ Configure max connections appropriately
- ✅ Monitor memory usage
- ✅ Set up backups

#### Monitoring
```python
# Regular health checks
stats = redis_memory.get_memory_stats()
if stats['total_keys'] > 10000:
    logger.warning("High key count, consider cleanup")
```

---

## Integration Examples

### With FastAPI Endpoints

```python
from fastapi import APIRouter, Depends
from app.services.redis_memory import get_redis_memory

router = APIRouter()

@router.post("/chat")
async def chat(
    agent_id: str,
    session_id: str,
    message: str,
    redis_memory = Depends(get_redis_memory)
):
    # Get history
    history = redis_memory.get_conversation_history(agent_id, session_id)

    # Process with agent
    # ... agent logic ...

    # Save updated history
    redis_memory.append_to_history(agent_id, session_id, new_message)

    return {"response": response}
```

### With Celery Tasks

```python
from celery import shared_task
from app.services.redis_memory import get_redis_memory

@shared_task
def cleanup_old_sessions():
    redis_memory = get_redis_memory()
    # Cleanup logic
    ...
```

---

## Support

For issues or questions:
- Check logs in `./logs/app.log`
- Run connection test: `python test_redis_connection.py`
- Review examples: `python examples/redis_memory_example.py`
- Run tests: `pytest tests/test_redis_memory.py -v`

---

**Version**: 0.1.0
**Last Updated**: December 2025
