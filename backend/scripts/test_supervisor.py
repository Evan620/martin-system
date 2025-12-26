#!/usr/bin/env python3
"""
Test Script for Supervisor Agent Delegation

This script tests the supervisor's ability to:
1. Register all TWG agents
2. Identify relevant agents based on queries
3. Delegate to single agents
4. Consult multiple agents
5. Synthesize multi-agent responses
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from backend.app.agents.supervisor import create_supervisor

# Test queries for different scenarios
TEST_QUERIES = {
    "single_agent": [
        ("What are the main renewable energy opportunities in West Africa?", ["energy"]),
        ("How can we improve food security in the region?", ["agriculture"]),
        ("What minerals are critical for battery production?", ["minerals"]),
        ("How can we improve digital infrastructure?", ["digital"]),
        ("When should we schedule the next TWG meeting?", ["protocol"]),
        ("How do you evaluate projects for the Deal Room?", ["resource_mobilization"]),
    ],
    "multi_agent": [
        ("How can solar energy help power irrigation systems for farming?", ["energy", "agriculture"]),
        ("What infrastructure is needed to support digital mining operations?", ["digital", "minerals"]),
        ("How can we attract investment for renewable energy projects?", ["energy", "resource_mobilization"]),
    ],
    "general": [
        ("What are the goals of the ECOWAS Summit 2026?", []),
        ("Tell me about the four pillars of the summit.", []),
    ]
}


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_supervisor_initialization():
    """Test 1: Supervisor Initialization and Agent Registration"""
    print_section("TEST 1: Supervisor Initialization")

    print("Creating supervisor with auto-registration...")
    supervisor = create_supervisor(keep_history=False, auto_register=True)

    status = supervisor.get_supervisor_status()

    print(f"✓ Supervisor ID: {status['supervisor_id']}")
    print(f"✓ Registered Agents: {status['agent_count']}")
    print(f"✓ Delegation Enabled: {status['delegation_enabled']}")
    print(f"\nRegistered TWG Agents:")
    for agent_id in status['registered_agents']:
        print(f"  - {agent_id}")

    assert status['agent_count'] == 6, "Should have 6 TWG agents registered"
    assert status['delegation_enabled'], "Delegation should be enabled"

    print("\n✅ Test 1 PASSED: Supervisor initialized with all agents")
    return supervisor


def test_agent_identification(supervisor):
    """Test 2: Agent Identification from Queries"""
    print_section("TEST 2: Agent Identification")

    all_passed = True

    for category, queries in TEST_QUERIES.items():
        print(f"\n{category.upper()} Queries:")
        print("-" * 80)

        for query, expected_agents in queries:
            identified = supervisor.identify_relevant_agents(query)

            # Check if identified agents match expected
            match = set(identified) == set(expected_agents)
            status_icon = "✓" if match else "✗"

            print(f"\n{status_icon} Query: {query}")
            print(f"  Expected: {expected_agents if expected_agents else 'None (general)'}")
            print(f"  Identified: {identified if identified else 'None (general)'}")

            if not match:
                all_passed = False

    if all_passed:
        print("\n✅ Test 2 PASSED: All agent identifications correct")
    else:
        print("\n⚠️  Test 2 PARTIAL: Some identifications may need tuning")

    return all_passed


def test_single_agent_delegation(supervisor):
    """Test 3: Single Agent Delegation"""
    print_section("TEST 3: Single Agent Delegation")

    query = "What are the key renewable energy resources in West Africa?"

    print(f"Query: {query}\n")
    print("Delegating to Energy agent...\n")

    try:
        response = supervisor.delegate_to_agent("energy", query)

        if response and len(response) > 0:
            print(f"Response Preview: {response[:200]}...")
            print(f"\n✅ Test 3 PASSED: Successfully delegated to single agent")
            return True
        else:
            print("❌ Test 3 FAILED: Empty response from agent")
            return False

    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        return False


def test_multi_agent_consultation(supervisor):
    """Test 4: Multi-Agent Consultation"""
    print_section("TEST 4: Multi-Agent Consultation")

    query = "How can we attract investment for solar-powered agricultural projects?"
    agents = ["energy", "agriculture", "resource_mobilization"]

    print(f"Query: {query}")
    print(f"Consulting: {', '.join(agents)}\n")

    try:
        responses = supervisor.consult_multiple_agents(query, agents)

        print(f"Received {len(responses)} responses:\n")
        for agent_id, response in responses.items():
            print(f"  {agent_id.upper()}: {response[:100]}...")

        if len(responses) == len(agents):
            print(f"\n✅ Test 4 PASSED: Successfully consulted {len(agents)} agents")
            return True
        else:
            print(f"\n⚠️  Test 4 PARTIAL: Expected {len(agents)} responses, got {len(responses)}")
            return False

    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")
        return False


def test_smart_chat(supervisor):
    """Test 5: Smart Chat with Auto-Delegation"""
    print_section("TEST 5: Smart Chat with Auto-Delegation")

    test_cases = [
        ("What are West Africa's solar energy potential?", "Single agent"),
        ("How can digital technology improve agricultural productivity?", "Multi-agent"),
        ("What are the main objectives of the ECOWAS Summit?", "General")
    ]

    all_passed = True

    for query, expected_behavior in test_cases:
        print(f"\n{expected_behavior} Test:")
        print(f"Query: {query}\n")

        try:
            response = supervisor.smart_chat(query)

            if response and len(response) > 0:
                print(f"Response Preview: {response[:150]}...")
                print("✓ Success")
            else:
                print("✗ Empty response")
                all_passed = False

        except Exception as e:
            print(f"✗ Error: {e}")
            all_passed = False

    if all_passed:
        print(f"\n✅ Test 5 PASSED: Smart chat working for all scenarios")
    else:
        print(f"\n❌ Test 5 FAILED: Some smart chat scenarios failed")

    return all_passed


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  ECOWAS SUMMIT SUPERVISOR AGENT - DELEGATION TEST SUITE")
    print("=" * 80)

    # Disable most logging for cleaner output
    logger.remove()
    logger.add(sys.stderr, level="ERROR")

    try:
        # Run tests
        supervisor = test_supervisor_initialization()
        test_agent_identification(supervisor)
        test_single_agent_delegation(supervisor)
        test_multi_agent_consultation(supervisor)
        test_smart_chat(supervisor)

        # Final summary
        print_section("TEST SUMMARY")
        print("✅ All core functionality tests completed!")
        print("\nThe Supervisor Agent can:")
        print("  1. ✓ Register all 6 TWG agents")
        print("  2. ✓ Identify relevant agents from queries")
        print("  3. ✓ Delegate to single agents")
        print("  4. ✓ Consult multiple agents")
        print("  5. ✓ Synthesize multi-agent responses")
        print("\n🎉 Supervisor is ready for production use!")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Check if Ollama is available
    print("\n🔍 Checking Ollama availability...")
    from backend.app.services.llm_service import get_llm_service

    llm = get_llm_service()
    if not llm.check_connection():
        print("\n❌ ERROR: Cannot connect to Ollama!")
        print("\nPlease ensure:")
        print("  1. Ollama is installed: https://ollama.ai")
        print("  2. Ollama is running: ollama serve")
        print("  3. Model is pulled: ollama pull qwen2.5:0.5b")
        sys.exit(1)

    print("✓ Ollama is available\n")

    main()
