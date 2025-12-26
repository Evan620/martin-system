#!/usr/bin/env python3
"""
Test Document Synthesis and Global Scheduling

Tests the supervisor's ability to:
1. Synthesize TWG sections into coherent Declaration
2. Enforce terminology consistency and citation
3. Schedule cross-TWG events with conflict detection
4. Coordinate VIP engagements
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.supervisor import create_supervisor


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_declaration_synthesis():
    """Test 1: Synthesizing Declaration from TWG sections"""
    print_section("TEST 1: Declaration Synthesis")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("Simulating TWG Declaration sections...")
    print()

    # Simulate TWG sections (in real scenario, these come from agents)
    twg_sections = {
        "energy": """
We commit to accelerating regional power integration through the West African Power Pool.
Target: 5000 MW of renewable capacity by 2026. $15 billion investment needed.
WAPP will enable cross-border electricity trade across all 15 member states.
        """.strip(),

        "agriculture": """
For agriculture, our priority is mechanization to double productivity.
We'll establish agricultural value chains in all member states.
Investment target: $8 billion for rural infrastructure.
WAPP expansion will power irrigation systems and processing facilities.
        """.strip(),

        "digital": """
Digital transformation requires regional broadband connectivity.
Target: 100% fintech interoperability by 2027.
E-commerce platforms will integrate across borders.
Investment: $5 billion for digital infrastructure.
        """.strip()
    }

    print("Synthesizing Declaration with:")
    print("  • Terminology standardization")
    print("  • Voice harmonization")
    print("  • Citation enforcement")
    print()

    # Create simple knowledge base
    knowledge_base = {
        "sources": {
            "energy": ["ECOWAS Energy Protocol 2023", "WAPP Master Plan 2025"],
            "agriculture": ["Regional Agriculture Investment Plan 2024"],
            "digital": ["ECOWAS Digital Economy Strategy 2025"]
        }
    }

    # Note: In real implementation, would call:
    # result = supervisor.synthesize_declaration(collect_from_twgs=True)
    # For testing, we use pre-defined sections

    result = supervisor.document_synthesizer.synthesize_declaration(
        twg_sections=twg_sections,
        title="ECOWAS Summit 2026 Declaration",
        preamble="We, the Heads of State and Government of ECOWAS member states, gathered in summit...",
        knowledge_base=knowledge_base
    )

    print("Synthesis Results:")
    print("-" * 70)
    print(f"Document length: {result['metadata']['word_count']} words")
    print(f"Sections synthesized: {len(result['metadata']['sections'])}")
    print(f"Coherence score: {result['metadata']['coherence_score']:.1%}")
    print(f"Terminology changes: {result['synthesis_log']['terminology_changes']}")
    print(f"Voice adjustments: {result['synthesis_log']['voice_adjustments']}")
    print(f"Citations added: {result['synthesis_log']['citations_added']}")
    print()

    if result['metadata']['issues']:
        print("Issues detected:")
        for issue in result['metadata']['issues']:
            print(f"  ⚠️  {issue}")
    else:
        print("✓ No coherence issues detected")

    print()
    print("Declaration Preview (first 500 chars):")
    print("-" * 70)
    print(result['document'][:500] + "...")
    print("-" * 70)

    return True


def test_global_scheduling():
    """Test 2: Global scheduling with conflict detection"""
    print_section("TEST 2: Global Scheduling")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("Scheduling cross-TWG events with conflict detection...")
    print()

    # Schedule Event 1: Energy TWG meeting
    result1 = supervisor.schedule_event(
        event_type="twg_meeting",
        title="Energy TWG Technical Session",
        start_time=datetime(2026, 3, 15, 9, 0),
        duration_minutes=120,
        required_twgs=["energy"],
        priority="medium",
        location="Conference Room A"
    )

    print(f"Event 1: {result1['status'].upper()}")
    print(f"  {result1['event'].title}")
    print(f"  {result1['event'].start_time.strftime('%Y-%m-%d %H:%M')}")
    print()

    # Schedule Event 2: Overlapping with Event 1 (same TWG)
    result2 = supervisor.schedule_event(
        event_type="ministerial_prep",
        title="Energy-Agriculture Coordination",
        start_time=datetime(2026, 3, 15, 10, 0),  # Overlaps!
        duration_minutes=180,
        required_twgs=["energy", "agriculture"],
        priority="high"
    )

    print(f"Event 2: {result2['status'].upper()}")
    print(f"  {result2['event'].title}")
    print(f"  {result2['event'].start_time.strftime('%Y-%m-%d %H:%M')}")

    if result2['status'] == 'conflict':
        print(f"  ⚠️  {len(result2['conflicts'])} conflicts detected:")
        for conflict in result2['conflicts']:
            print(f"    - {conflict.description}")

        if result2.get('alternative_times'):
            print(f"  ✓ Alternative times suggested:")
            for alt_time in result2['alternative_times'][:3]:
                print(f"    - {alt_time.strftime('%Y-%m-%d %H:%M')}")
    print()

    # Schedule Event 3: VIP engagement
    result3 = supervisor.schedule_event(
        event_type="vip_engagement",
        title="Ministerial Roundtable on Regional Integration",
        start_time=datetime(2026, 3, 15, 14, 0),
        duration_minutes=120,
        required_twgs=["energy", "agriculture", "minerals", "digital"],
        priority="critical",
        vip_attendees=["Minister of Energy", "Minister of Agriculture"],
        location="VIP Lounge"
    )

    print(f"Event 3: {result3['status'].upper()}")
    print(f"  {result3['event'].title}")
    print(f"  Participants: {len(result3['event'].required_twgs)} TWGs")
    print(f"  VIPs: {len(result3['event'].vip_attendees)}")
    print()

    # Get scheduling summary
    summary = supervisor.get_scheduling_summary()

    print("Scheduling Summary:")
    print("-" * 70)
    print(f"Total events: {summary['total_events']}")
    print(f"By type: {summary['by_type']}")
    print(f"By priority: {summary['by_priority']}")
    print(f"Total conflicts: {summary['total_conflicts']}")
    print(f"Critical conflicts: {summary['critical_conflicts']}")
    print("-" * 70)

    return True


def test_twg_schedule_view():
    """Test 3: TWG-specific schedule view"""
    print_section("TEST 3: TWG Schedule View")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    # Schedule multiple events
    base_time = datetime(2026, 3, 15, 9, 0)

    supervisor.schedule_event(
        event_type="twg_meeting",
        title="Energy TWG Planning Session",
        start_time=base_time,
        duration_minutes=120,
        required_twgs=["energy"]
    )

    supervisor.schedule_event(
        event_type="coordination_meeting",
        title="Energy-Agriculture Coordination",
        start_time=base_time + timedelta(hours=3),
        duration_minutes=90,
        required_twgs=["energy", "agriculture"]
    )

    supervisor.schedule_event(
        event_type="ministerial_prep",
        title="Pre-Summit Ministerial Briefing",
        start_time=base_time + timedelta(hours=5),
        duration_minutes=120,
        required_twgs=["energy", "agriculture", "minerals"]
    )

    # Get Energy TWG schedule
    energy_schedule = supervisor.get_twg_schedule("energy")

    print(f"Energy TWG Schedule ({len(energy_schedule)} events):")
    print("-" * 70)

    for event in energy_schedule:
        print(f"{event.start_time.strftime('%H:%M')} - {event.end_time.strftime('%H:%M')}")
        print(f"  {event.title}")
        print(f"  Type: {event.event_type.value}, Priority: {event.priority.value}")
        print(f"  Participants: {', '.join(event.required_twgs)}")
        print()

    print("-" * 70)

    return True


def test_conflict_detection():
    """Test 4: Comprehensive conflict detection"""
    print_section("TEST 4: Schedule Conflict Detection")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("Creating intentional scheduling conflicts...")
    print()

    base_time = datetime(2026, 3, 20, 10, 0)

    # Event 1: Energy meeting
    supervisor.schedule_event(
        event_type="twg_meeting",
        title="Energy Technical Session",
        start_time=base_time,
        duration_minutes=120,
        required_twgs=["energy"],
        location="Room A"
    )

    # Event 2: Same TWG, overlapping time (CONFLICT)
    supervisor.schedule_event(
        event_type="deal_room_session",
        title="Energy Deal Room Preparation",
        start_time=base_time + timedelta(minutes=60),  # Overlaps
        duration_minutes=90,
        required_twgs=["energy"]
    )

    # Event 3: Same location, overlapping time (CONFLICT)
    supervisor.schedule_event(
        event_type="twg_meeting",
        title="Agriculture Planning",
        start_time=base_time + timedelta(minutes=30),  # Overlaps
        duration_minutes=120,
        required_twgs=["agriculture"],
        location="Room A"  # Same location!
    )

    # Detect all conflicts
    conflicts = supervisor.detect_schedule_conflicts()

    print(f"Detected {len(conflicts)} conflicts:")
    print("-" * 70)

    for i, conflict in enumerate(conflicts, 1):
        print(f"\nConflict #{i}:")
        print(f"  Type: {conflict.conflict_type}")
        print(f"  Severity: {conflict.severity.upper()}")
        print(f"  Events: {', '.join(conflict.event_titles)}")
        print(f"  Description: {conflict.description}")
        print(f"  Impact: {conflict.impact}")

        if conflict.suggested_resolution:
            print(f"  Suggestion: {conflict.suggested_resolution}")

    print()
    print("-" * 70)

    return True


def main():
    """Run all synthesis and scheduling tests"""
    print("\n" + "=" * 70)
    print("  DOCUMENT SYNTHESIS AND GLOBAL SCHEDULING TESTS")
    print("=" * 70)
    print("\nThis test suite demonstrates the Supervisor's ability to:")
    print("  1. Synthesize TWG outputs into coherent Declaration")
    print("  2. Enforce terminology consistency and citations")
    print("  3. Schedule cross-TWG events with conflict detection")
    print("  4. Coordinate VIP engagements")
    print()

    tests = [
        ("Declaration Synthesis", test_declaration_synthesis),
        ("Global Scheduling", test_global_scheduling),
        ("TWG Schedule View", test_twg_schedule_view),
        ("Conflict Detection", test_conflict_detection)
    ]

    # Let user choose which test to run
    print("Available tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print(f"  {len(tests) + 1}. Run all tests")

    try:
        choice = input("\nSelect test to run (1-5): ").strip()
        choice_num = int(choice)

        if 1 <= choice_num <= len(tests):
            # Run single test
            name, test_func = tests[choice_num - 1]
            print(f"\nRunning: {name}")
            test_func()
            print(f"\n✅ Test completed!")

        elif choice_num == len(tests) + 1:
            # Run all tests
            print("\nRunning all tests...")
            for name, test_func in tests:
                try:
                    test_func()
                    print(f"\n✅ {name} completed!")
                except Exception as e:
                    print(f"\n❌ {name} failed: {e}")
                    import traceback
                    traceback.print_exc()

            print("\n" + "=" * 70)
            print("  ALL TESTS COMPLETED")
            print("=" * 70)

        else:
            print("Invalid choice!")
            return 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
