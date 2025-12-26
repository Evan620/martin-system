#!/usr/bin/env python3
"""
Quick test to see the new multi-agent display format
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.supervisor import create_supervisor

def main():
    print("\n" + "=" * 70)
    print("Testing Multi-Agent Display Format")
    print("=" * 70 + "\n")

    # Create supervisor with registered agents
    print("Creating supervisor and registering agents...")
    supervisor = create_supervisor(auto_register=True, keep_history=False)

    print(f"Registered {len(supervisor.get_registered_agents())} agents")
    print(f"Agents: {supervisor.get_registered_agents()}\n")

    # Test multi-agent query
    query = "What are the meeting logistics for organizing the investor forum?"

    print(f"Query: {query}\n")
    print("Consulting agents...\n")
    print("=" * 70)

    response = supervisor.smart_chat(query)

    print("\n" + "=" * 70)
    print("RESPONSE:")
    print("=" * 70)
    print(response)
    print("=" * 70)

if __name__ == "__main__":
    main()
