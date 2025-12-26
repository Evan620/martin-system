#!/usr/bin/env python3
"""
Test Broadcast and Conflict Resolution Features

Tests the supervisor's ability to:
1. Broadcast strategic context to all agents
2. Detect conflicts between TWG outputs
3. Facilitate automated negotiation to resolve conflicts
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.supervisor import create_supervisor


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_broadcast_strategic_context():
    """Test 1: Broadcasting strategic context to all agents"""
    print_section("TEST 1: Broadcast Strategic Context")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("Broadcasting strategic context to all TWG agents...")
    print("\nContext includes:")
    print("  • Summit objectives")
    print("  • Strategic priorities")
    print("  • Policy constraints")
    print("  • Cross-cutting themes")
    print()

    results = supervisor.broadcast_strategic_context(
        summit_objectives=[
            "Accelerate regional integration through infrastructure connectivity",
            "Mobilize $50 billion in strategic investments by 2026",
            "Strengthen ECOWAS institutional capacity for implementation",
            "Position West Africa as global leader in renewable energy and digital economy"
        ],
        strategic_priorities=[
            "WAPP expansion to 5000 MW renewable capacity by 2026",
            "Regional digital payment interoperability across all 15 member states",
            "Agricultural value chain modernization to double productivity",
            "Critical minerals processing hubs in 5 member states"
        ],
        policy_constraints=[
            "All projects must align with ECOWAS Protocol on Energy",
            "Climate neutrality required for all energy infrastructure projects",
            "Local content requirements: minimum 40% regional sourcing",
            "Gender equity targets: 30% women participation in all programs"
        ],
        cross_cutting_themes=[
            "Youth employment (target: 100,000 jobs created)",
            "Climate resilience and green growth",
            "Gender equity and women empowerment",
            "Digital inclusion and connectivity"
        ],
        coordination_points={
            "energy_agriculture": "Rural electrification to enable agricultural mechanization",
            "digital_all": "Digital platforms for TWG coordination and reporting",
            "minerals_energy": "Renewable energy for mining operations",
            "resource_mobilization_all": "Coordinated investor engagement across all pillars"
        },
        version="1.0"
    )

    print("Broadcast Results:")
    print("-" * 70)
    for agent_id, success in results.items():
        status = "✓ Delivered" if success else "✗ Failed"
        print(f"  {agent_id:25s} {status}")
    print("-" * 70)

    successful = sum(1 for s in results.values() if s)
    print(f"\n✅ Strategic context broadcast to {successful}/{len(results)} agents")

    # Verify context is stored
    active_context = supervisor.get_active_context()
    if active_context:
        print(f"\n✓ Active context version: {active_context.version}")
        print(f"  Summit objectives: {len(active_context.summit_objectives)}")
        print(f"  Strategic priorities: {len(active_context.strategic_priorities)}")

    return True


def test_broadcast_document():
    """Test 2: Broadcasting key documents to all agents"""
    print_section("TEST 2: Broadcast Key Document")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("Broadcasting ECOWAS Summit Concept Note to all agents...")
    print()

    results = supervisor.broadcast_document(
        document_type="concept_note",
        title="ECOWAS Summit 2026 Concept Note",
        version="2.1",
        summary="""
The ECOWAS Summit 2026 aims to accelerate regional integration through four
strategic pillars: Energy & Infrastructure, Agriculture & Food Security,
Critical Minerals & Industrialization, and Digital Economy. The summit will
feature a high-level Deal Room targeting $50B in investments.
        """.strip(),
        key_points=[
            "Four strategic pillars with dedicated TWG coordination",
            "Deal Room target: $50 billion investment pipeline",
            "Expected participation: 15 Heads of State, 500+ investors, 200+ projects",
            "Declaration to be adopted covering regional integration framework",
            "Implementation period: 2026-2030 with quarterly progress reviews"
        ],
        relevant_sections={
            "energy": ["Section 3: Energy & Infrastructure Pillar", "Annex A: WAPP Framework"],
            "agriculture": ["Section 4: Agriculture & Food Security", "Annex B: Value Chain Programs"],
            "minerals": ["Section 5: Critical Minerals Strategy", "Annex C: Processing Hubs"],
            "digital": ["Section 6: Digital Economy Roadmap", "Annex D: Connectivity Targets"]
        }
    )

    print("Broadcast Results:")
    print("-" * 70)
    for agent_id, success in results.items():
        status = "✓ Delivered" if success else "✗ Failed"
        print(f"  {agent_id:25s} {status}")
    print("-" * 70)

    successful = sum(1 for s in results.values() if s)
    print(f"\n✅ Document broadcast to {successful}/{len(results)} agents")

    return True


def test_conflict_detection():
    """Test 3: Detecting conflicts between TWG outputs"""
    print_section("TEST 3: Conflict Detection")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("Creating simulated TWG outputs with intentional conflicts...")
    print()

    # Simulated outputs with conflicts
    twg_outputs = {
        "energy": """
Our key policy recommendation is to achieve 100% renewable energy by 2030.
This means phasing out all fossil fuel infrastructure. We recommend:
- Target: 5000 MW renewable capacity by 2026
- No new coal or gas power plants
- $15 billion investment in solar and wind
        """,
        "minerals": """
Our strategy includes building 3 coal-fired smelting plants for aluminum processing.
These plants are essential for industrialization and will require:
- 2000 MW baseload power from coal plants
- $5 billion investment in coal infrastructure
- Target: 500,000 tons aluminum production by 2028
        """,
        "agriculture": """
We propose mechanization through electrification of rural areas.
Need 1500 MW rural power by 2027. We recommend:
- Solar mini-grids for 5000 villages
- $8 billion investment in rural electrification
- Partnership with energy TWG on grid expansion
        """,
        "digital": """
Our digital infrastructure requires 800 MW stable power for data centers.
We propose using natural gas for reliability. Targets:
- 10 regional data centers powered by gas
- $3 billion investment in gas-powered facilities
- Backup renewable integration for 30% of power
        """
    }

    print("Running conflict detection across all TWG outputs...")
    print()

    conflicts = supervisor.detect_conflicts(twg_outputs=twg_outputs)

    if conflicts:
        print(f"⚠️  Detected {len(conflicts)} conflicts:\n")
        for i, conflict in enumerate(conflicts, 1):
            print(f"Conflict #{i}:")
            print(f"  Type: {conflict.conflict_type}")
            print(f"  Severity: {conflict.severity.upper()}")
            print(f"  Agents: {', '.join(conflict.agents_involved)}")
            print(f"  Description: {conflict.description}")
            print(f"  Impact: {conflict.impact}")
            print(f"  Requires negotiation: {'Yes' if conflict.requires_negotiation else 'No'}")
            print()
    else:
        print("✓ No conflicts detected")

    # Get conflict summary
    summary = supervisor.get_conflict_summary()
    print("Conflict Summary:")
    print(f"  Total: {summary['total_conflicts']}")
    print(f"  By severity: {summary['by_severity']}")
    print(f"  Unresolved: {summary['unresolved']}")

    return len(conflicts) > 0


def test_automated_negotiation():
    """Test 4: Automated negotiation to resolve conflicts"""
    print_section("TEST 4: Automated Negotiation")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("Detecting conflicts for negotiation...")
    print()

    # Use the same conflicting outputs
    twg_outputs = {
        "energy": "Target: 100% renewable by 2030, no fossil fuels",
        "minerals": "Need coal-fired smelting plants for aluminum processing",
    }

    conflicts = supervisor.detect_conflicts(twg_outputs=twg_outputs)

    if not conflicts:
        print("⚠️  No conflicts detected - using simulated conflict")
        # Create a simulated conflict for testing
        from app.schemas.broadcast_messages import create_conflict_alert
        conflict = create_conflict_alert(
            conflict_type="policy_target",
            severity="high",
            agents_involved=["energy", "minerals"],
            description="Energy TWG targets 100% renewables while Minerals TWG proposes coal infrastructure",
            conflicting_positions={
                "energy": "100% renewable energy by 2030, phase out all fossil fuels",
                "minerals": "Coal-fired smelting plants needed for aluminum processing"
            },
            impact="Major policy inconsistency affecting investment decisions",
            urgency="high",
            suggested_resolution="Explore renewable-powered smelting alternatives or phased approach",
            requires_negotiation=True,
            requires_human_intervention=False
        )
        conflicts = [conflict]

    conflict = conflicts[0]
    print(f"Initiating negotiation for conflict:")
    print(f"  Type: {conflict.conflict_type}")
    print(f"  Agents: {', '.join(conflict.agents_involved)}")
    print(f"  Issue: {conflict.description}")
    print()

    print("Starting automated negotiation (max 3 rounds)...")
    print()

    result = supervisor.initiate_negotiation(
        conflict,
        constraints=[
            "Must align with ECOWAS climate commitments",
            "Must support industrialization goals",
            "Solution must be financially viable"
        ],
        max_rounds=3
    )

    print("Negotiation Result:")
    print("-" * 70)
    print(f"  Status: {result['status']}")

    if result["status"] == "resolved":
        print(f"  ✅ Consensus achieved!")
        print(f"  Resolution: {result.get('resolution', 'N/A')}")
        print(f"  Rounds: {result.get('rounds', 0)}")
    elif result["status"] == "escalated":
        print(f"  ⚠️  Escalated to human intervention")
        print(f"  Reason: {result.get('reason', 'N/A')}")
        if 'summary' in result:
            print(f"\n  Escalation Summary:")
            print(f"  {result['summary']}")
    else:
        print(f"  🔄 In progress")
        print(f"  Round: {result.get('round', 0)}")

    print("-" * 70)

    return True


def test_auto_resolve_conflicts():
    """Test 5: Bulk automated conflict resolution"""
    print_section("TEST 5: Automated Conflict Resolution (Full Cycle)")

    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print("This test runs the complete conflict resolution cycle:")
    print("  1. Detect conflicts across all TWGs")
    print("  2. Automatically initiate negotiations")
    print("  3. Resolve conflicts or escalate")
    print()

    print("Running auto-resolve (this may take 30-60 seconds)...")
    print()

    summary = supervisor.auto_resolve_conflicts()

    print("Auto-Resolution Summary:")
    print("-" * 70)
    print(f"  Total conflicts: {summary['total_conflicts']}")
    print(f"  Resolved: {summary['resolved']}")
    print(f"  Escalated: {summary['escalated']}")
    print(f"  In progress: {summary['in_progress']}")
    print(f"  Resolution rate: {summary['resolution_rate']:.1%}")
    print(f"  Message: {summary['message']}")
    print("-" * 70)

    if summary['resolution_rate'] >= 0.9:
        print("\n✅ Achieved 90%+ automated resolution target!")
    elif summary['total_conflicts'] == 0:
        print("\n✓ No conflicts detected - all TWGs aligned")
    else:
        print(f"\n⚠️  Resolution rate: {summary['resolution_rate']:.1%}")

    return True


def main():
    """Run all broadcast and conflict resolution tests"""
    print("\n" + "=" * 70)
    print("  BROADCAST AND CONFLICT RESOLUTION TESTING")
    print("=" * 70)
    print("\nThis test suite demonstrates the Supervisor's ability to:")
    print("  1. Broadcast strategic context to ensure consistent strategic playbook")
    print("  2. Detect policy conflicts and contradictions")
    print("  3. Facilitate automated negotiation between agents")
    print("  4. Achieve 90%+ automated consensus-building")
    print()

    tests = [
        ("Broadcast Strategic Context", test_broadcast_strategic_context),
        ("Broadcast Key Document", test_broadcast_document),
        ("Conflict Detection", test_conflict_detection),
        ("Automated Negotiation", test_automated_negotiation),
        ("Auto-Resolve Conflicts", test_auto_resolve_conflicts)
    ]

    # Let user choose which test to run
    print("Available tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print(f"  {len(tests) + 1}. Run all tests")

    try:
        choice = input("\nSelect test to run (1-6): ").strip()
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
