#!/usr/bin/env python3
"""
Test Script for Multi-Agent Routing

Tests the enhanced keyword-based routing to verify multi-agent detection.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.supervisor import create_supervisor


def test_routing():
    """Test the routing logic with various queries"""

    print("\n" + "=" * 70)
    print("Testing Enhanced Multi-Agent Routing")
    print("=" * 70)

    # Create supervisor (no need to register agents for routing test)
    supervisor = create_supervisor(auto_register=False)

    # Test queries
    test_cases = [
        # Single agent queries
        ("What are ECOWAS renewable energy targets?", ["energy"]),
        ("Tell me about agricultural modernization", ["agriculture"]),
        ("What is the lithium mining strategy?", ["minerals"]),

        # Multi-agent queries (2 agents)
        ("How can digital technology improve agricultural productivity?", ["digital", "agriculture"]),
        ("What role does energy play in mining industrialization?", ["energy", "minerals"]),
        ("How can we secure investment and financing for renewable energy projects?", ["resource_mobilization", "energy"]),
        ("What are the meeting logistics for organizing the investor forum?", ["protocol", "resource_mobilization"]),

        # Complex multi-agent queries (3+ agents)
        ("How can we attract investment to develop renewable energy for agricultural processing?",
         ["resource_mobilization", "energy", "agriculture"]),
        ("What digital technology supports mining operations?", ["digital", "minerals"]),
    ]

    print("\nRunning routing tests...\n")

    passed = 0
    failed = 0

    for query, expected_agents in test_cases:
        print(f"Query: {query[:70]}...")

        # Get identified agents
        identified = supervisor.identify_relevant_agents(query)

        # Check if all expected agents were identified
        expected_set = set(expected_agents)
        identified_set = set(identified)

        if expected_set == identified_set:
            print(f"  ✅ PASS: Identified {identified}")
            passed += 1
        elif expected_set.issubset(identified_set):
            extra = identified_set - expected_set
            print(f"  ⚠️  PARTIAL: Identified {identified} (extra: {extra})")
            passed += 1
        else:
            missing = expected_set - identified_set
            print(f"  ❌ FAIL: Expected {expected_agents}, got {identified}")
            print(f"     Missing: {missing}")
            failed += 1

        print()

    # Summary
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)

    if failed == 0:
        print("\n✅ All routing tests passed! Multi-agent detection is working.\n")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review keyword mappings.\n")
        return False


if __name__ == "__main__":
    success = test_routing()
    sys.exit(0 if success else 1)
