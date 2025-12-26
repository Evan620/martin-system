# Document Synthesis and Global Scheduling

The Supervisor agent includes powerful capabilities for synthesizing TWG outputs into coherent documents and managing global scheduling across all TWGs. This completes the "hive" architecture where the Supervisor acts as the command center coordinating all worker bee activities.

## Table of Contents

1. [Overview](#overview)
2. [Document Synthesis](#document-synthesis)
3. [Global Scheduling](#global-scheduling)
4. [Architecture](#architecture)
5. [Usage Examples](#usage-examples)
6. [Best Practices](#best-practices)

---

## Overview

### The Hive Architecture

```
         ┌──────────────────┐
         │   SUPERVISOR     │  ← Queen/Command Center
         │  (Coordinator)   │
         └────────┬─────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
┌─────▼────┐ ┌───▼────┐ ┌───▼────┐
│ Energy   │ │ Agri   │ │ Digital│  ← Worker Bees
│  TWG     │ │  TWG   │ │  TWG   │     (Specialized)
└──────────┘ └────────┘ └────────┘
```

**Parallelization**: Each TWG works independently on its domain
**Unity**: Supervisor ensures consistency, coherence, and coordination

###Key Capabilities

1. **Document Synthesis**:
   - Compiles TWG sections into unified documents
   - Ensures consistent voice and terminology
   - Enforces citation of knowledge base sources
   - Prevents hallucinated data in policy drafts

2. **Global Scheduling**:
   - Prevents overlaps and conflicts
   - Ensures proper sequencing of dependent events
   - Coordinates VIP engagements across TWGs
   - Manages critical path to summit

---

## Document Synthesis

### What Gets Synthesized

The Supervisor can synthesize:

1. **Declarations** - Summit declarations with ministerial voice
2. **Summit Reports** - Technical reports across all pillars
3. **Policy Briefs** - Executive summaries for stakeholders
4. **Concept Notes** - Planning documents
5. **Technical Reports** - Detailed analysis documents

### Synthesis Features

#### 1. Terminology Standardization

Ensures consistent terminology across all sections.

**Problem**:
- Energy TWG uses "WAPP"
- Agriculture TWG uses "West African Power Pool"
- Digital TWG uses "regional power grid"

**Solution**:
The synthesizer standardizes to: "West African Power Pool (WAPP)" on first use, then "WAPP" thereafter.

```python
# Add terminology standard
supervisor.add_terminology_standard(
    twg_id="energy",
    abbreviation="WAPP",
    full_term="West African Power Pool"
)
```

#### 2. Voice Harmonization

Ensures all sections use the same voice and tone.

**Styles Available**:
- `formal_ministerial` - For Declarations ("We, the Heads of State...")
- `technical` - For technical reports (objective, data-driven)
- `executive` - For executive summaries (clear, concise)
- `policy` - For policy briefs (action-oriented)

**Example**:

Before harmonization:
- Energy TWG: "The energy sector needs investment..."
- Agriculture TWG: "We commit to transforming agriculture..."

After harmonization (formal_ministerial):
- Energy: "We commit to accelerating energy sector development..."
- Agriculture: "We commit to transforming agricultural systems..."

#### 3. Citation Enforcement

Prevents hallucinated data by requiring citations for factual claims.

**What Gets Cited**:
- Numerical claims: "$50 billion", "5000 MW", "100%"
- Statistics: "increase of 25%", "growth rate of 8%"
- Policy references: "ECOWAS Protocol", "Regional Agreement"
- Historical facts: "Since 2020...", "In 2023..."

**Example**:

Before citation:
```
Target: 5000 MW renewable capacity by 2026.
Investment needed: $15 billion.
```

After citation:
```
Target: 5000 MW renewable capacity by 2026 [Source: WAPP Master Plan 2025].
Investment needed: $15 billion [Source: ECOWAS Energy Protocol 2023].
```

#### 4. Coherence Checking

Final check for:
- Terminology consistency
- Voice consistency (first person vs third person)
- Citation coverage
- Formatting uniformity

**Coherence Score**: 0.0 - 1.0 (target: 0.9+)

### Usage: Synthesizing a Declaration

```python
from app.agents.supervisor import create_supervisor

# Create supervisor
supervisor = create_supervisor(auto_register=True)

# Method 1: Automatic collection from TWGs
result = supervisor.synthesize_declaration(
    title="ECOWAS Summit 2026 Declaration",
    preamble="We, the Heads of State and Government...",
    collect_from_twgs=True  # Automatically queries all TWGs
)

# Method 2: Manual TWG sections
twg_sections = {
    "energy": "Energy section content...",
    "agriculture": "Agriculture section content...",
    "minerals": "Minerals section content..."
}

result = supervisor.document_synthesizer.synthesize_declaration(
    twg_sections=twg_sections,
    title="ECOWAS Summit 2026 Declaration",
    knowledge_base=my_knowledge_base  # For citations
)

# Access results
print(result['document'])  # The synthesized Declaration
print(f"Coherence: {result['metadata']['coherence_score']:.1%}")
print(f"Citations added: {result['synthesis_log']['citations_added']}")
```

---

## Global Scheduling

### Scheduling Capabilities

1. **Conflict Detection**:
   - Time overlaps for same TWGs
   - Dependency violations
   - VIP availability conflicts
   - Location double-booking

2. **Smart Scheduling**:
   - Suggests alternative times
   - Respects event priorities
   - Handles dependencies
   - Critical path analysis

3. **Event Types**:
   - `twg_meeting` - Single TWG meetings
   - `ministerial_prep` - Ministerial preparation meetings
   - `vip_engagement` - VIP engagements requiring multiple TWGs
   - `technical_session` - Technical sessions
   - `deal_room_session` - Deal Room preparation
   - `coordination_meeting` - Cross-TWG coordination
   - `deadline` - Important deadlines

### Priority Levels

- **Critical** - Ministerial, VIP engagements (must not conflict)
- **High** - Multi-TWG coordination (important)
- **Medium** - Single TWG meetings (normal)
- **Low** - Optional sessions (can be rescheduled)

### Usage: Scheduling Events

#### Example 1: Simple TWG Meeting

```python
result = supervisor.schedule_event(
    event_type="twg_meeting",
    title="Energy TWG Technical Session",
    start_time=datetime(2026, 3, 15, 9, 0),
    duration_minutes=120,
    required_twgs=["energy"],
    priority="medium",
    location="Conference Room A"
)

if result['status'] == 'scheduled':
    print(f"✓ Scheduled: {result['event'].title}")
else:
    print(f"⚠️ Conflict: {result['conflicts']}")
```

#### Example 2: Ministerial Prep (Multiple TWGs)

```python
result = supervisor.schedule_event(
    event_type="ministerial_prep",
    title="Pre-Summit Ministerial Coordination",
    start_time=datetime(2026, 3, 15, 14, 0),
    duration_minutes=180,
    required_twgs=["energy", "agriculture", "minerals"],
    priority="critical",
    vip_attendees=["Minister of Energy", "Minister of Agriculture"],
    description="Final coordination before summit"
)
```

#### Example 3: VIP Engagement

```python
result = supervisor.schedule_event(
    event_type="vip_engagement",
    title="Presidential Roundtable on Regional Integration",
    start_time=datetime(2026, 3, 20, 10, 0),
    duration_minutes=120,
    required_twgs=["energy", "agriculture", "minerals", "digital"],
    priority="critical",
    vip_attendees=[
        "President of Nigeria",
        "President of Ghana",
        "ECOWAS Commission Chairman"
    ],
    location="VIP Lounge"
)

# Check for conflicts
if result['status'] == 'conflict':
    print("Conflicts detected:")
    for conflict in result['conflicts']:
        print(f"  - {conflict.description}")

    print("\nAlternative times:")
    for alt_time in result['alternative_times']:
        print(f"  - {alt_time.strftime('%Y-%m-%d %H:%M')}")
```

### Viewing Schedules

#### TWG-Specific Schedule

```python
# Get Energy TWG schedule for March 2026
events = supervisor.get_twg_schedule(
    twg_id="energy",
    start_date=datetime(2026, 3, 1),
    end_date=datetime(2026, 3, 31)
)

for event in events:
    print(f"{event.start_time.strftime('%H:%M')} - {event.title}")
    print(f"  Participants: {', '.join(event.required_twgs)}")
```

#### Global Schedule (All TWGs)

```python
# Get global schedule
schedule = supervisor.get_global_schedule(
    start_date=datetime(2026, 3, 1),
    end_date=datetime(2026, 3, 31)
)

print(f"Total events in March: {len(schedule)}")

# Group by day
from collections import defaultdict
by_day = defaultdict(list)

for event in schedule:
    day = event.start_time.date()
    by_day[day].append(event)

for day, events in sorted(by_day.items()):
    print(f"\n{day.strftime('%B %d, %Y')}:")
    for event in events:
        print(f"  {event.start_time.strftime('%H:%M')} - {event.title}")
```

### Detecting Schedule Conflicts

```python
# Detect all conflicts in current schedule
conflicts = supervisor.detect_schedule_conflicts()

print(f"Found {len(conflicts)} conflicts")

for conflict in conflicts:
    print(f"\n{conflict.severity.upper()}: {conflict.conflict_type}")
    print(f"  Events: {', '.join(conflict.event_titles)}")
    print(f"  Impact: {conflict.impact}")

    if conflict.suggested_resolution:
        print(f"  Suggestion: {conflict.suggested_resolution}")
```

### Scheduling Summary

```python
summary = supervisor.get_scheduling_summary()

print(f"Total events: {summary['total_events']}")
print(f"By type: {summary['by_type']}")
print(f"By priority: {summary['by_priority']}")
print(f"Total conflicts: {summary['total_conflicts']}")
print(f"Critical conflicts: {summary['critical_conflicts']}")
```

---

## Architecture

### Components

```
Supervisor Agent
├── DocumentSynthesizer
│   ├── synthesize_declaration()
│   ├── _standardize_terminology()
│   ├── _harmonize_voice()
│   └── _enforce_citations()
└── GlobalScheduler
    ├── schedule_event()
    ├── _detect_conflicts()
    ├── _suggest_alternative_times()
    └── get_twg_schedule()
```

### Key Files

- **[document_synthesizer.py](../app/services/document_synthesizer.py)** - Document synthesis logic
- **[global_scheduler.py](../app/services/global_scheduler.py)** - Scheduling and conflict detection
- **[supervisor.py](../app/agents/supervisor.py)** - Integration layer
- **[test_synthesis_scheduling.py](../test_synthesis_scheduling.py)** - Test suite

---

## Usage Examples

### Example 1: Pre-Summit Document Preparation

```python
# 1. Broadcast strategic context to all TWGs
supervisor.broadcast_strategic_context(
    summit_objectives=[...],
    strategic_priorities=[...]
)

# 2. Collect Declaration sections from TWGs
result = supervisor.synthesize_declaration(
    title="ECOWAS Summit 2026 Declaration",
    collect_from_twgs=True
)

# 3. Review coherence
if result['metadata']['coherence_score'] < 0.9:
    print("Issues to address:")
    for issue in result['metadata']['issues']:
        print(f"  - {issue}")

# 4. Save Declaration
with open("declaration_draft.md", "w") as f:
    f.write(result['document'])
```

### Example 2: Summit Week Scheduling

```python
from datetime import datetime, timedelta

summit_week = datetime(2026, 3, 15)

# Day 1: TWG final preparations
supervisor.schedule_event(
    event_type="twg_meeting",
    title="Energy TWG Final Review",
    start_time=summit_week.replace(hour=9),
    duration_minutes=120,
    required_twgs=["energy"]
)

# Day 2: Ministerial coordination
supervisor.schedule_event(
    event_type="ministerial_prep",
    title="Multi-Pillar Ministerial Briefing",
    start_time=(summit_week + timedelta(days=1)).replace(hour=10),
    duration_minutes=180,
    required_twgs=["energy", "agriculture", "minerals", "digital"],
    priority="critical",
    vip_attendees=["All Ministers"]
)

# Day 3: Presidential summit
supervisor.schedule_event(
    event_type="vip_engagement",
    title="ECOWAS Presidential Summit",
    start_time=(summit_week + timedelta(days=2)).replace(hour=9),
    duration_minutes=360,
    required_twgs=["protocol", "resource_mobilization"],
    priority="critical",
    vip_attendees=["15 Heads of State"]
)

# Check for conflicts
conflicts = supervisor.detect_schedule_conflicts()
if conflicts:
    print(f"⚠️ {len(conflicts)} conflicts to resolve")
```

### Example 3: Terminology Standardization

```python
# Define terminology standards
supervisor.add_terminology_standard("energy", "WAPP", "West African Power Pool")
supervisor.add_terminology_standard("agriculture", "RAIP", "Regional Agriculture Investment Plan")
supervisor.add_terminology_standard("digital", "ECOFIN", "ECOWAS Financial Network")

# These will be automatically applied during synthesis
result = supervisor.synthesize_declaration(collect_from_twgs=True)
```

---

## Best Practices

### Document Synthesis

1. **Collect Early**: Collect TWG sections well before deadline to allow time for synthesis
2. **Provide Knowledge Base**: Always provide knowledge base for accurate citations
3. **Review Coherence**: Target 0.9+ coherence score before finalization
4. **Iterate**: Synthesize → Review → Refine TWG sections → Re-synthesize

### Global Scheduling

1. **Schedule Critical First**: Schedule VIP and ministerial events first, fill around them
2. **Buffer Time**: Add 30-minute buffers between events for VIPs
3. **Check Dependencies**: Ensure prerequisite events complete before dependent ones
4. **Monitor Conflicts**: Run daily conflict checks as schedule evolves

### General

1. **Hive Coordination**: Let TWGs work in parallel, supervisor coordinates
2. **Consistent Voice**: Use same synthesis style for all summit documents
3. **Citation Culture**: Enforce citations to build trust in outputs
4. **Proactive Scheduling**: Schedule major events 3+ months in advance

---

## Testing

### Run the Test Suite

```bash
cd backend
python3 test_synthesis_scheduling.py
```

Available tests:

1. **Declaration Synthesis** - Tests terminology, voice, citations
2. **Global Scheduling** - Tests event scheduling and conflict detection
3. **TWG Schedule View** - Tests TWG-specific schedule retrieval
4. **Conflict Detection** - Tests comprehensive conflict detection

### Expected Outcomes

- ✅ Declaration synthesized with 0.9+ coherence
- ✅ Terminology standardized across sections
- ✅ Voice harmonized to formal ministerial style
- ✅ Citations added for numerical claims
- ✅ Schedule conflicts detected and resolved
- ✅ Alternative times suggested for conflicts

---

## Performance Considerations

### Document Synthesis

- **Time**: 30-60 seconds for 6 TWG sections
- **LLM Calls**: N sections × 2 (terminology + voice) = 12 calls for 6 TWGs
- **Optimization**: Cache terminology standards, batch voice harmonization

### Global Scheduling

- **Time**: <1 second for conflict detection
- **Scalability**: O(n²) for n events (pairwise conflict checks)
- **Optimization**: Index events by time range, early termination

---

## Future Enhancements

Planned improvements:

1. **Multi-Language Synthesis**: French, Portuguese for ECOWAS
2. **Visual Document Editor**: Real-time collaborative editing
3. **Smart Calendaring**: AI-powered optimal scheduling
4. **Citation Database**: Integrated knowledge base with auto-citation
5. **Version Control**: Track document evolution with diffs
6. **Export Formats**: PDF, DOCX, PowerPoint generation

---

**Last Updated**: 2025-12-26
**Version**: 1.0.0
