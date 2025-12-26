# Quick Start: Broadcast & Conflict Resolution

## 5-Minute Guide to Using the New Supervisor Capabilities

### 1. Broadcasting Strategic Context

```python
from app.agents.supervisor import create_supervisor

# Create supervisor
supervisor = create_supervisor(auto_register=True)

# Broadcast strategic context to all agents
supervisor.broadcast_strategic_context(
    summit_objectives=[
        "Accelerate regional integration",
        "Mobilize $50B investments"
    ],
    strategic_priorities=[
        "WAPP expansion to 5000 MW by 2026",
        "Digital payment interoperability"
    ],
    policy_constraints=[
        "Climate neutrality for energy projects",
        "40% local content requirements"
    ]
)
```

**Result**: All 6 TWG agents now reference the same strategic playbook.

---

### 2. Detecting Conflicts

```python
# Auto-detect conflicts across all TWGs
conflicts = supervisor.detect_conflicts()

# Review conflicts
for conflict in conflicts:
    print(f"{conflict.severity}: {conflict.description}")
    print(f"Involves: {', '.join(conflict.agents_involved)}")
```

**Example Output**:
```
high: Energy TWG targets 100% renewables while Minerals TWG proposes coal infrastructure
Involves: energy, minerals
```

---

### 3. Auto-Resolving Conflicts (The Magic ✨)

```python
# One-line automatic conflict resolution
summary = supervisor.auto_resolve_conflicts()

# Check results
print(f"Resolved: {summary['resolved']}/{summary['total_conflicts']}")
print(f"Success rate: {summary['resolution_rate']:.1%}")
```

**Target**: 90%+ resolution rate (minor conflicts resolved, major ones escalated)

---

### 4. Manual Negotiation (For Specific Conflicts)

```python
# Detect conflicts
conflicts = supervisor.detect_conflicts()

# Manually negotiate the first one
result = supervisor.initiate_negotiation(
    conflict=conflicts[0],
    constraints=["Must align with ECOWAS protocols"],
    max_rounds=3
)

if result["status"] == "resolved":
    print(f"✅ Consensus: {result['resolution']}")
else:
    print(f"⚠️ Escalated: {result['reason']}")
```

---

### 5. Complete Daily Workflow

```python
# Morning: Set context for the day
supervisor.broadcast_strategic_context(...)

# Afternoon: Check for conflicts
conflicts = supervisor.detect_conflicts(
    query="What are your latest recommendations?"
)

# Auto-resolve what you can
summary = supervisor.auto_resolve_conflicts(conflicts)

# Review escalations
if summary['escalated'] > 0:
    escalated = supervisor.conflict_detector.get_conflicts(
        status="escalated"
    )
    for conflict in escalated:
        print(f"⚠️ Needs review: {conflict.description}")
```

---

## Real-World Example

### Scenario: Energy vs. Minerals Conflict

**Energy TWG says**: "100% renewable energy by 2030, no fossil fuels"
**Minerals TWG says**: "We need coal-fired smelting plants for aluminum"

```python
# 1. Detect the conflict
conflicts = supervisor.detect_conflicts()
# → Detects: "Policy target contradiction (high severity)"

# 2. Auto-negotiate
result = supervisor.initiate_negotiation(
    conflict=conflicts[0],
    constraints=[
        "Must support climate goals",
        "Must enable industrialization"
    ]
)

# 3. Possible outcomes:
# ✅ RESOLVED: "Use renewable-powered electric arc furnaces for smelting"
# OR
# ⚠️ ESCALATED: "Fundamental policy divergence - needs Ministerial decision"
```

---

## Testing Your Setup

```bash
# Run the test suite
cd backend
python3 test_broadcast_conflict.py

# Select test:
# 1. Broadcast Strategic Context
# 2. Broadcast Key Document
# 3. Conflict Detection
# 4. Automated Negotiation
# 5. Auto-Resolve Conflicts
# 6. Run all tests
```

---

## Key Metrics

Monitor these to track system performance:

```python
# Conflict summary
conflict_summary = supervisor.get_conflict_summary()
print(f"Total conflicts: {conflict_summary['total_conflicts']}")
print(f"Unresolved: {conflict_summary['unresolved']}")

# Negotiation summary
negotiation_summary = supervisor.get_negotiation_summary()
print(f"Success rate: {negotiation_summary['success_rate']:.1%}")
```

**Target Metrics**:
- Conflict detection: 100% of actual conflicts
- Auto-resolution rate: 90%+
- Escalation rate: <10%

---

## Common Use Cases

### Use Case 1: Pre-Summit Alignment Check

```python
# Ensure all TWGs aligned before summit
summary = supervisor.auto_resolve_conflicts()

if summary['resolution_rate'] >= 0.9:
    print("✅ Ready for summit!")
else:
    print(f"⚠️ Only {summary['resolution_rate']:.1%} resolved")
```

### Use Case 2: Document Update Notification

```python
# Notify all agents of new Declaration draft
supervisor.broadcast_document(
    document_type="declaration_draft",
    title="ECOWAS Declaration 2026",
    version="3.2",
    summary="Updated declaration incorporating TWG feedback...",
    key_points=["New climate targets", "Updated investment goals"]
)
```

### Use Case 3: Policy Constraint Enforcement

```python
# Add new constraint and check for conflicts
supervisor.broadcast_strategic_context(
    policy_constraints=[
        "All projects must be climate-neutral by 2030"  # NEW
    ],
    version="2.0"
)

# See if any TWG proposals violate this
conflicts = supervisor.detect_conflicts()
```

---

## Troubleshooting

**Q: Broadcasts not being received?**
A: Check agents are registered: `supervisor.get_registered_agents()`

**Q: No conflicts detected when they should be?**
A: Try semantic detection (LLM-based) - it catches nuanced conflicts

**Q: Negotiations always escalate?**
A: Review constraints - they may be too restrictive

**Q: Too slow?**
A: Use brief queries for conflict detection, limit to specific agents

---

## Next Steps

1. ✅ Test with `python3 test_broadcast_conflict.py`
2. 📖 Read full docs: [BROADCAST_AND_CONFLICT_RESOLUTION.md](./BROADCAST_AND_CONFLICT_RESOLUTION.md)
3. 🚀 Integrate into your workflow
4. 📊 Monitor metrics and optimize

---

**Last Updated**: 2025-12-26
