# Broadcast and Conflict Resolution System

The Supervisor agent includes powerful capabilities for broadcasting strategic context to all TWG agents and automatically detecting and resolving conflicts between their outputs. This enables **90%+ automated consensus-building** before content reaches Ministers.

## Table of Contents

1. [Overview](#overview)
2. [Strategic Context Broadcasting](#strategic-context-broadcasting)
3. [Conflict Detection](#conflict-detection)
4. [Automated Negotiation](#automated-negotiation)
5. [Architecture](#architecture)
6. [Usage Examples](#usage-examples)
7. [Best Practices](#best-practices)

---

## Overview

### The Problem

In multi-agent TWG systems, two critical challenges emerge:

1. **Context Fragmentation**: Each agent may work with different assumptions about Summit objectives, policies, and priorities
2. **Inter-TWG Conflicts**: TWGs may propose contradictory policies, overlapping sessions, or incompatible targets

### The Solution

The Supervisor agent provides:

1. **Broadcasting**: Distributes strategic context (Summit objectives, core documents, policy constraints) to ensure all agents work from the same playbook
2. **Conflict Detection**: Automatically identifies contradictions, overlaps, and policy divergences
3. **Automated Negotiation**: Facilitates multi-round agent-to-agent negotiation to build consensus
4. **Smart Escalation**: Only escalates to humans when automated resolution fails

### Key Benefits

- **Consistency**: All agents reference the same strategic framework
- **Efficiency**: 90%+ of conflicts resolved without human intervention
- **Early Detection**: Catches issues before they reach Ministers
- **Transparency**: Full audit trail of conflicts and resolutions

---

## Strategic Context Broadcasting

### What Gets Broadcast

The Supervisor can broadcast:

1. **Strategic Context**:
   - Summit objectives
   - Strategic priorities
   - Policy constraints and guardrails
   - Cross-cutting themes (youth, gender, climate)
   - Coordination requirements

2. **Documents**:
   - Concept Notes
   - Declaration drafts
   - Policy frameworks
   - Strategic playbooks
   - Guidelines and reference materials

### How It Works

```python
# Broadcasting strategic context
supervisor.broadcast_strategic_context(
    summit_objectives=[
        "Accelerate regional integration through infrastructure",
        "Mobilize $50B in strategic investments"
    ],
    strategic_priorities=[
        "WAPP expansion to 5000 MW by 2026",
        "Digital payment interoperability"
    ],
    policy_constraints=[
        "All projects must align with ECOWAS protocols",
        "Climate neutrality required for energy projects"
    ],
    cross_cutting_themes=[
        "Youth employment",
        "Climate resilience",
        "Gender equity"
    ],
    coordination_points={
        "energy_agriculture": "Rural electrification enables mechanization",
        "digital_all": "Digital platforms for coordination"
    }
)
```

### Broadcast Lifecycle

1. **Creation**: Supervisor creates broadcast with content
2. **Delivery**: Broadcast injected into each agent's context
3. **Acknowledgement**: Agents can acknowledge receipt (optional)
4. **Storage**: Broadcast stored in history for audit trail
5. **Versioning**: New broadcasts can supersede previous versions

### Document Broadcasting

```python
# Broadcasting a key document
supervisor.broadcast_document(
    document_type="concept_note",
    title="ECOWAS Summit 2026 Concept Note",
    version="2.1",
    summary="Framework for regional integration summit...",
    key_points=[
        "Four strategic pillars",
        "Deal Room target: $50B",
        "15 Heads of State expected"
    ],
    relevant_sections={
        "energy": ["Section 3: Energy Pillar", "Annex A: WAPP"],
        "agriculture": ["Section 4: Agriculture", "Annex B: Value Chains"]
    }
)
```

---

## Conflict Detection

### Types of Conflicts Detected

1. **Policy Targets**:
   - Contradictory goals (e.g., "100% renewables" vs "coal plants")
   - Incompatible numerical targets
   - Timeline conflicts

2. **Resource Allocation**:
   - Competing budget requests
   - Overlapping funding needs
   - Priority conflicts

3. **Session Overlaps**:
   - Concurrent session proposals
   - Venue double-booking
   - Schedule conflicts

4. **Policy Directions**:
   - Contradictory recommendations
   - Incompatible regulatory proposals
   - Mandate conflicts

5. **Technology Choices**:
   - Incompatible technology standards
   - Platform conflicts
   - Infrastructure contradictions

### Detection Methods

The conflict detector uses three complementary approaches:

#### 1. Pattern-Based Detection

Scans for keyword patterns that signal potential conflicts:

```python
# Example: Renewable energy vs fossil fuels
Energy TWG: "100% renewable by 2030"
Minerals TWG: "coal-fired smelting plants"
→ CONFLICT DETECTED: Policy target contradiction
```

#### 2. Target Analysis

Extracts and compares numerical targets:

```python
# Extracts: "100% renewable", "5000 MW", "$50 billion"
# Checks for: contradictions, overlaps, resource conflicts
```

#### 3. Semantic Analysis (LLM-powered)

Uses LLM to understand nuanced conflicts:

```python
# LLM analyzes full context to detect:
# - Implicit contradictions
# - Subtle policy divergences
# - Dependency conflicts
```

### Conflict Severity Levels

- **Critical**: Major policy contradiction, immediate attention needed
- **High**: Significant conflict affecting key priorities
- **Medium**: Moderate issue requiring coordination
- **Low**: Minor overlap, easy to resolve

### Example: Detecting Conflicts

```python
# Collect TWG outputs
conflicts = supervisor.detect_conflicts()

# Or provide specific outputs
twg_outputs = {
    "energy": "Target: 100% renewable by 2030",
    "minerals": "Need coal plants for aluminum smelting"
}
conflicts = supervisor.detect_conflicts(twg_outputs=twg_outputs)

# Review conflicts
for conflict in conflicts:
    print(f"{conflict.severity}: {conflict.description}")
    print(f"Agents: {conflict.agents_involved}")
    print(f"Requires negotiation: {conflict.requires_negotiation}")
```

---

## Automated Negotiation

### How Negotiation Works

When a conflict is detected, the Supervisor can initiate automated negotiation:

1. **Initiation**: Supervisor creates negotiation request
2. **Round 1**: Each agent proposes a compromise
3. **Analysis**: Supervisor analyzes proposals for consensus
4. **Iteration**: If no consensus, provides guidance and starts Round 2
5. **Resolution**: Either consensus is reached or negotiation is escalated

### Negotiation Modes

1. **Consensus**: Agents work toward full agreement
2. **Compromise**: Agents meet in the middle
3. **Arbitration**: Supervisor determines best path (future)

### Example: Manual Negotiation

```python
# Detect conflicts
conflicts = supervisor.detect_conflicts()

# Initiate negotiation for first conflict
result = supervisor.initiate_negotiation(
    conflict=conflicts[0],
    constraints=[
        "Must align with ECOWAS protocols",
        "Must support climate goals"
    ],
    max_rounds=3
)

# Check result
if result["status"] == "resolved":
    print(f"✅ Consensus: {result['resolution']}")
elif result["status"] == "escalated":
    print(f"⚠️ Needs human intervention: {result['reason']}")
```

### Example: Automated Resolution

```python
# Detect conflicts AND auto-resolve them
summary = supervisor.auto_resolve_conflicts()

print(f"Total conflicts: {summary['total_conflicts']}")
print(f"Resolved: {summary['resolved']}")
print(f"Escalated: {summary['escalated']}")
print(f"Resolution rate: {summary['resolution_rate']:.1%}")

# Target: 90%+ resolution rate
```

### Negotiation Constraints

You can specify non-negotiable constraints:

```python
result = supervisor.initiate_negotiation(
    conflict,
    constraints=[
        "Must align with ECOWAS climate commitments",
        "Must support industrialization goals",
        "Solution must be financially viable"
    ]
)
```

These constraints guide agents during proposal development.

### Escalation to Humans

Negotiation escalates when:

- No consensus after max rounds (default: 3)
- Conflict marked as requiring human intervention
- Technical error during negotiation

Escalation includes:

- Summary of all negotiation rounds
- Final positions of each agent
- Recommended next steps

---

## Architecture

### Components

```
Supervisor Agent
├── BroadcastService
│   ├── broadcast_message()
│   ├── broadcast_context()
│   └── broadcast_document()
├── ConflictDetector
│   ├── detect_conflicts()
│   ├── detect_pattern_conflicts()
│   ├── detect_target_conflicts()
│   └── detect_semantic_conflicts()
└── NegotiationService
    ├── initiate_negotiation()
    ├── run_negotiation()
    └── analyze_proposals()
```

### Key Files

- **[broadcast_messages.py](../app/schemas/broadcast_messages.py)** - Message schemas
- **[broadcast_service.py](../app/services/broadcast_service.py)** - Broadcasting logic
- **[conflict_detector.py](../app/services/conflict_detector.py)** - Conflict detection
- **[negotiation_service.py](../app/services/negotiation_service.py)** - Negotiation facilitation
- **[supervisor.py](../app/agents/supervisor.py)** - Integration layer

### Message Flow

```
┌──────────────┐
│  Supervisor  │
└──────┬───────┘
       │ broadcast_strategic_context()
       ├──────────────────────────────────┐
       │                                  │
       ▼                                  ▼
┌─────────────┐                    ┌─────────────┐
│  Energy TWG │                    │  Minerals   │
└─────────────┘                    └─────────────┘
       │                                  │
       │ (both receive same context)     │
       │                                  │
       └──────────┬───────────────────────┘
                  │
                  ▼
           All agents work from
           same strategic playbook
```

### Conflict Detection Flow

```
┌──────────────┐
│  Supervisor  │
└──────┬───────┘
       │ detect_conflicts()
       │
       ▼
┌──────────────────┐
│ ConflictDetector │
└──────┬───────────┘
       │
       ├─► Pattern-based detection
       ├─► Target analysis
       └─► Semantic analysis (LLM)
       │
       ▼
  List of conflicts
       │
       ▼
┌──────────────────┐
│ NegotiationSvc   │ (if auto-negotiate)
└──────────────────┘
```

---

## Usage Examples

### Example 1: Setting Up Strategic Context

```python
from app.agents.supervisor import create_supervisor

# Create supervisor with all TWGs
supervisor = create_supervisor(auto_register=True)

# Broadcast strategic context at start of summit planning
supervisor.broadcast_strategic_context(
    summit_objectives=[
        "Accelerate regional integration",
        "Mobilize $50B investments",
        "Strengthen institutional capacity"
    ],
    strategic_priorities=[
        "WAPP expansion to 5000 MW",
        "Agricultural productivity doubling",
        "Digital payment interoperability"
    ],
    policy_constraints=[
        "Climate neutrality for energy projects",
        "40% local content requirements",
        "30% gender equity targets"
    ],
    cross_cutting_themes=[
        "Youth employment: 100,000 jobs",
        "Climate resilience",
        "Gender equity"
    ]
)
```

### Example 2: Daily Conflict Check

```python
# Run daily to catch emerging conflicts early
conflicts = supervisor.detect_conflicts(
    query="What are your latest policy recommendations?"
)

# Auto-resolve what you can
summary = supervisor.auto_resolve_conflicts(conflicts)

# Review what needs escalation
if summary['escalated'] > 0:
    print(f"⚠️ {summary['escalated']} conflicts need human review")

    # Get details on escalated conflicts
    escalated = supervisor.conflict_detector.get_conflicts(status="escalated")
    for conflict in escalated:
        print(f"- {conflict.description}")
```

### Example 3: Pre-Summit Validation

```python
# Before summit, ensure all TWGs are aligned
print("Running pre-summit alignment check...")

# 1. Broadcast final context
supervisor.broadcast_strategic_context(...)

# 2. Detect any remaining conflicts
conflicts = supervisor.detect_conflicts()

# 3. Auto-resolve
summary = supervisor.auto_resolve_conflicts()

# 4. Validate success
if summary['resolution_rate'] >= 0.9:
    print("✅ 90%+ alignment achieved - ready for summit!")
else:
    print(f"⚠️ Only {summary['resolution_rate']:.1%} resolved")
    print("Review escalated conflicts before proceeding")
```

### Example 4: Versioned Context Updates

```python
# Initial context
supervisor.broadcast_strategic_context(
    summit_objectives=[...],
    version="1.0"
)

# Update context as priorities evolve
supervisor.broadcast_strategic_context(
    summit_objectives=[...],  # Updated objectives
    version="2.0"
)

# Agents automatically receive updated context
# Previous version is superseded
```

---

## Best Practices

### Broadcasting

1. **Early and Often**: Broadcast context at the start and update as priorities evolve
2. **Versioning**: Use version numbers to track context evolution
3. **Specificity**: Be specific in objectives and constraints
4. **Relevance**: Use `relevant_sections` to highlight agent-specific content

### Conflict Detection

1. **Regular Checks**: Run conflict detection daily or after major TWG updates
2. **Comprehensive Queries**: Use broad queries to capture full TWG positions
3. **Threshold Tuning**: Adjust severity thresholds based on your needs
4. **Manual Review**: Always review critical conflicts, even if auto-resolved

### Automated Negotiation

1. **Set Constraints**: Provide clear, non-negotiable constraints
2. **Max Rounds**: Use 3 rounds for most conflicts, 5 for complex ones
3. **Trust the Process**: 90% resolution is the target - some escalation is OK
4. **Learn and Iterate**: Review escalated conflicts to improve constraints

### Monitoring

1. **Track Metrics**: Monitor resolution rates over time
2. **Escalation Patterns**: Identify types of conflicts that frequently escalate
3. **Agent Performance**: See which agents negotiate well vs. escalate
4. **Audit Trail**: Maintain broadcast and negotiation history for accountability

---

## Testing

### Run the Test Suite

```bash
cd backend
python3 test_broadcast_conflict.py
```

Available tests:

1. **Broadcast Strategic Context** - Tests context distribution
2. **Broadcast Key Document** - Tests document distribution
3. **Conflict Detection** - Tests pattern, target, and semantic detection
4. **Automated Negotiation** - Tests multi-round negotiation
5. **Auto-Resolve Conflicts** - Tests full cycle

### Expected Outcomes

- ✅ Strategic context delivered to all agents
- ✅ Documents broadcast with agent-specific sections
- ✅ Conflicts detected across pattern, target, and semantic layers
- ✅ Negotiations reach consensus or escalate appropriately
- ✅ 90%+ resolution rate in auto-resolve mode

---

## Performance Considerations

### Broadcast Performance

- **Time**: ~1-2 seconds to broadcast to all 6 agents
- **Scalability**: O(n) where n = number of agents
- **Storage**: Broadcasts stored in memory (add Redis for persistence)

### Conflict Detection Performance

- **Time**:
  - Pattern-based: ~1 second
  - Target analysis: ~2 seconds
  - Semantic (LLM): ~30 seconds per agent pair
- **Optimization**: Run semantic analysis only for high-priority conflicts

### Negotiation Performance

- **Time**: ~20-40 seconds per round (LLM calls)
- **Max Time**: 3 rounds = 60-120 seconds
- **Optimization**: Use brief queries, limit proposal length

---

## Future Enhancements

Planned improvements:

1. **Redis Persistence**: Store broadcasts and negotiations in Redis
2. **Async Negotiations**: Run multiple negotiations in parallel
3. **Smart Escalation**: ML-based prediction of which conflicts need humans
4. **Negotiation Analytics**: Detailed metrics on negotiation effectiveness
5. **Multi-Language**: Broadcast in French, Portuguese for ECOWAS
6. **Visual Dashboard**: Real-time view of conflicts and resolutions
7. **Agent Voting**: Agents can vote on proposals to accelerate consensus

---

## Troubleshooting

### Broadcasts Not Delivered

**Problem**: Agents not receiving broadcasts

**Solutions**:
- Check that agents are registered: `supervisor.get_registered_agents()`
- Verify agents support broadcast context (check `_broadcast_context` attribute)
- Review logs for delivery errors

### Conflicts Not Detected

**Problem**: Obvious conflicts not flagged

**Solutions**:
- Ensure TWG outputs have sufficient content
- Check keyword patterns in `conflict_detector.py`
- Try semantic detection if pattern-based misses it
- Lower severity threshold for testing

### Negotiations Always Escalate

**Problem**: No conflicts getting auto-resolved

**Solutions**:
- Review constraints - are they too restrictive?
- Increase max_rounds to give more time
- Check LLM responses in logs - is analysis working?
- Try simpler conflicts first to validate flow

### Performance Issues

**Problem**: Operations taking too long

**Solutions**:
- Reduce number of agents queried
- Use brief queries for conflict detection
- Disable semantic detection for routine checks
- Run negotiations serially, not in batch

---

**Last Updated**: 2025-12-26
**Version**: 1.0.0
