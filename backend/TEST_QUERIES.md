# Agent Coordination Test Queries

This document provides test queries to verify agent coordination, delegation, and the message bus system.

---

## 🎯 How to Test

### Start the Chat Interface

```bash
cd backend
python3 scripts/chat_agent.py --agent supervisor
```

The terminal will show:
- **Supervisor responses** in green
- **Delegated agent** indicated by `[Consulted {AGENT} TWG]`
- **Redis memory** status on startup

---

## 📋 Test Categories

### 1. Single Agent Delegation Tests

These queries should trigger delegation to **one specific TWG agent**.

#### Energy Agent Tests
```
Query: "What are ECOWAS renewable energy targets?"
Expected: [Consulted ENERGY TWG]

Query: "Tell me about the West African Power Pool"
Expected: [Consulted ENERGY TWG]

Query: "What infrastructure projects are planned for energy?"
Expected: [Consulted ENERGY TWG]

Query: "Explain the regional electricity grid expansion"
Expected: [Consulted ENERGY TWG]
```

#### Agriculture Agent Tests
```
Query: "What are the food security initiatives in West Africa?"
Expected: [Consulted AGRICULTURE TWG]

Query: "Tell me about ECOWAS agricultural modernization programs"
Expected: [Consulted AGRICULTURE TWG]

Query: "What is the regional fertilizer strategy?"
Expected: [Consulted AGRICULTURE TWG]

Query: "How does ECOWAS support smallholder farmers?"
Expected: [Consulted AGRICULTURE TWG]
```

#### Minerals Agent Tests
```
Query: "What is ECOWAS's strategy for critical minerals?"
Expected: [Consulted MINERALS TWG]

Query: "Tell me about lithium mining in West Africa"
Expected: [Consulted MINERALS TWG]

Query: "What are the industrialization goals for mining?"
Expected: [Consulted MINERALS TWG]

Query: "How does ECOWAS manage mineral resource governance?"
Expected: [Consulted MINERALS TWG]
```

#### Digital Economy Agent Tests
```
Query: "What are the digital transformation initiatives?"
Expected: [Consulted DIGITAL TWG]

Query: "Tell me about fintech development in ECOWAS"
Expected: [Consulted DIGITAL TWG]

Query: "What is the regional e-commerce strategy?"
Expected: [Consulted DIGITAL TWG]

Query: "How is ECOWAS promoting broadband connectivity?"
Expected: [Consulted DIGITAL TWG]
```

#### Protocol Agent Tests
```
Query: "What are the logistics arrangements for the summit?"
Expected: [Consulted PROTOCOL TWG]

Query: "Tell me about venue selection criteria"
Expected: [Consulted PROTOCOL TWG]

Query: "What security measures are planned for the event?"
Expected: [Consulted PROTOCOL TWG]

Query: "How are VIP delegations being managed?"
Expected: [Consulted PROTOCOL TWG]
```

#### Resource Mobilization Agent Tests
```
Query: "What are the funding sources for ECOWAS projects?"
Expected: [Consulted RESOURCE_MOBILIZATION TWG]

Query: "Tell me about development partner engagement"
Expected: [Consulted RESOURCE_MOBILIZATION TWG]

Query: "What is the strategy for attracting private investment?"
Expected: [Consulted RESOURCE_MOBILIZATION TWG]

Query: "How does ECOWAS manage donor coordination?"
Expected: [Consulted RESOURCE_MOBILIZATION TWG]
```

---

### 2. Multi-Agent Consultation Tests

These queries are **specifically designed** to trigger consultation with **multiple agents** by including keywords from different TWG domains.

**How Multi-Agent Detection Works:**
- Each agent has **primary keywords** (10 points each) and **secondary keywords** (3 points each)
- An agent is considered relevant if it scores **5+ points** from a query
- Queries with keywords from multiple TWG domains will trigger multiple agents
- The supervisor will consult ALL relevant agents and synthesize their responses

#### Cross-TWG Queries (2 Agents)

```
Query: "How can digital technology improve agricultural productivity?"
Expected: DIGITAL (10) + AGRICULTURE (10) = Both consulted
Keywords: "digital technology" (DIGITAL primary) + "agricultural productivity" (AGRICULTURE primary)

Query: "What role does energy play in mining industrialization?"
Expected: ENERGY (10) + MINERALS (20) = Both consulted
Keywords: "energy" (ENERGY primary) + "mining" + "industrialization" (MINERALS primary)

Query: "How can we secure investment and financing for renewable energy projects?"
Expected: RESOURCE_MOBILIZATION (20) + ENERGY (10) = Both consulted
Keywords: "investment" + "financing" (RESOURCE_MOB primary) + "renewable energy" (ENERGY primary)

Query: "What are the meeting logistics for organizing the investor forum?"
Expected: PROTOCOL (20) + RESOURCE_MOBILIZATION (10) = Both consulted
Keywords: "meeting" + "logistics" (PROTOCOL primary) + "investor forum" (RESOURCE_MOB primary)

Query: "How does broadband internet support digital farming and agribusiness?"
Expected: DIGITAL (20) + AGRICULTURE (20) = Both consulted
Keywords: "broadband" + "internet" (DIGITAL primary) + "farming" + "agribusiness" (AGRICULTURE primary)

Query: "What financing is available for mining infrastructure and mineral extraction?"
Expected: RESOURCE_MOBILIZATION (10) + MINERALS (30) = Both consulted
Keywords: "financing" (RESOURCE_MOB primary) + "mining" + "mineral" + "extraction" (MINERALS primary)
```

#### Complex Multi-Agent Queries (3+ Agents)

```
Query: "How can we attract investment to develop renewable energy for agricultural processing and food production?"
Expected: RESOURCE_MOBILIZATION + ENERGY + AGRICULTURE = All 3 consulted
Keywords: "investment" + "renewable energy" + "agricultural" + "food production"

Query: "What digital technology and internet solutions support mining operations and mineral resource management?"
Expected: DIGITAL + MINERALS = Both consulted
Keywords: "digital technology" + "internet" + "mining operations" + "mineral resource"

Query: "What are the logistics and funding requirements for organizing the energy investment forum?"
Expected: PROTOCOL + RESOURCE_MOBILIZATION + ENERGY = All 3 consulted
Keywords: "logistics" + "funding" + "energy" + "investment forum"

Query: "How can fintech and digital platforms improve agricultural financing and farmer access to capital?"
Expected: DIGITAL + AGRICULTURE + RESOURCE_MOBILIZATION = All 3 consulted
Keywords: "fintech" + "digital platforms" + "agricultural financing" + "farmer" + "capital"
```

---

### 3. General Knowledge Tests

These should be handled by the **Supervisor directly** (no delegation).

```
Query: "What is ECOWAS?"
Expected: Direct supervisor response (no TWG consultation)

Query: "Who are the member states?"
Expected: Direct supervisor response

Query: "When was ECOWAS founded?"
Expected: Direct supervisor response

Query: "What are the main objectives of ECOWAS?"
Expected: Direct supervisor response
```

---

### 4. Conversation History Tests

These test **Redis memory persistence**.

#### Test A: History within same session
```
Step 1: "What are the energy targets?"
Step 2: "What about renewable specifically?"
        (Should reference previous energy context)
Step 3: "When will this be achieved?"
        (Should reference targets mentioned earlier)
```

#### Test B: Cross-session persistence
```
Session 1:
  - Start chat: python3 scripts/chat_agent.py --agent supervisor --session-id test123
  - Ask: "What are ECOWAS energy initiatives?"
  - Type: exit

Session 2:
  - Start chat: python3 scripts/chat_agent.py --agent supervisor --session-id test123
  - Ask: "What else did we discuss?"
  - Expected: Should recall the energy discussion from Session 1
```

---

### 5. Edge Cases & Error Handling

#### Ambiguous Queries
```
Query: "Tell me about development"
Expected: May trigger multiple agents or supervisor handles broadly

Query: "What about sustainability?"
Expected: Could involve multiple TWGs
```

#### Empty/Short Queries
```
Query: "Hello"
Expected: Supervisor greeting (no delegation)

Query: "Thanks"
Expected: Supervisor acknowledgment
```

---

## 🔍 What to Look For

### ✅ Successful Delegation Indicators

1. **Terminal Output Shows:**
   ```
   Supervisor: [Consulted ENERGY TWG]

   [Agent response here...]
   ```

2. **Logs Show (if --debug enabled):**
   ```
   INFO | Supervisor: Delegating to single agent: energy
   INFO | Energy agent initialized successfully
   ```

3. **Redis Memory Working:**
   - On startup: "✓ Redis memory enabled (Session: cli-xxxxx)"
   - Check: Type `info` command to see history length

### ❌ Issues to Watch For

1. **No Delegation Happening:**
   - Check if agents are registered (type `info` to verify)
   - Verify Ollama is running: `ollama serve`
   - Check model is loaded: `ollama run qwen2.5:0.5b`

2. **Errors:**
   - "Cannot connect to Ollama" → Start Ollama service
   - "Redis connection failed" → Check Redis: `brew services start redis`
   - Timeout errors → Model may be slow to respond

---

## 📊 Testing Checklist

- [ ] Single agent delegation works (test 2-3 agents)
- [ ] Multi-agent consultation works
- [ ] General queries handled by supervisor
- [ ] Conversation history persists within session
- [ ] Cross-session memory works with same session-id
- [ ] `info` command shows correct agent count
- [ ] `reset` command clears history
- [ ] Redis status shows healthy connection
- [ ] Terminal clearly shows which agent responded

---

## 🛠️ Debugging Commands

### In the Chat Interface:

```bash
info          # Show agent info, history length, Redis status
reset         # Clear conversation history
help          # Show available commands
quit/exit     # Exit the chat
```

### System Commands:

```bash
# Check Ollama status
ollama list

# Check Redis status
redis-cli ping

# View Redis keys for your session
redis-cli KEYS "ecowas:*"

# Check supervisor status in Python
python3 -c "
from app.agents.supervisor import create_supervisor
s = create_supervisor(auto_register=True)
print(s.get_supervisor_status())
"
```

---

## 🎨 Expected Terminal Output Examples

### Example 1: Single Agent Delegation

```
You: What are ECOWAS renewable energy targets?

Supervisor: [Consulted ENERGY TWG]

The ECOWAS region has set ambitious renewable energy targets...
[detailed response from Energy agent]
```

### Example 2: Multi-Agent Consultation

```
You: How can we finance renewable energy projects?

Supervisor: Based on consultations with Energy and Resource Mobilization TWGs:

**Energy Infrastructure Perspective:**
[Energy agent input]

**Financing Strategy:**
[Resource Mobilization agent input]

**Synthesis:**
To finance renewable energy projects, ECOWAS recommends...
```

### Example 3: Info Command

```
You: info

======================================================================
AGENT INFORMATION
======================================================================
Agent ID: supervisor
History Enabled: True
Max History: 20
Current History Length: 4

Redis Memory:
  Enabled: True
  Session ID: cli-abc12345
  TTL: 3600
  Connection: ✓ Healthy

Supervisor Status:
  Registered Agents: ['energy', 'agriculture', 'minerals', 'digital', 'protocol', 'resource_mobilization']
  Agent Count: 6
  Delegation Enabled: True

System Prompt Preview:
You are the Supervisor Agent for the ECOWAS Summit 2026...
======================================================================
```

---

## 📝 Notes

1. **First Response May Be Slow**: Ollama needs to load the model (~5-10 seconds)
2. **Session IDs**: Auto-generated if not specified (format: `cli-xxxxxxxx`)
3. **TTL**: CLI sessions expire after 1 hour by default
4. **Debug Mode**: Add `--debug` flag to see detailed logs
5. **No Redis**: Use `--no-redis` flag to test in-memory mode

---

## 🚀 Quick Start Testing Sequence

Run this sequence to verify everything works:

```bash
# 1. Start chat
python3 scripts/chat_agent.py --agent supervisor

# 2. Test single delegation
> What are renewable energy targets?

# 3. Test history
> What percentage is that?

# 4. Check status
> info

# 5. Test multi-agent
> How can we finance these energy projects?

# 6. Exit
> exit
```

Expected: All queries should work, show delegation, and maintain context.

---

**Happy Testing! 🎉**

Report any issues with:
- Which query was used
- Expected vs actual agent delegation
- Error messages (if any)
- Terminal output
