#!/usr/bin/env python3
"""
CLI Interface for Testing AI Agents

Provides an interactive command-line interface to chat with any of the
7 AI agents in the ECOWAS Summit TWG Support System.

Usage:
    python scripts/chat_agent.py --agent supervisor
    python scripts/chat_agent.py --agent energy
    python scripts/chat_agent.py --agent agriculture
    python scripts/chat_agent.py --agent minerals
    python scripts/chat_agent.py --agent digital
    python scripts/chat_agent.py --agent protocol
    python scripts/chat_agent.py --agent resource_mobilization
"""

import sys
import argparse
from pathlib import Path

# Add project root directory to path to allow importing backend modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from backend.app.agents.supervisor import create_supervisor
from backend.app.agents.energy_agent import create_energy_agent
from backend.app.agents.agriculture_agent import create_agriculture_agent
from backend.app.agents.minerals_agent import create_minerals_agent
from backend.app.agents.digital_agent import create_digital_agent
from backend.app.agents.protocol_agent import create_protocol_agent
from backend.app.agents.resource_mobilization_agent import create_resource_mobilization_agent
from backend.app.agents.prompts import list_agents


# Agent factory mapping
AGENT_FACTORY = {
    "supervisor": create_supervisor_with_tools,
    "energy": create_energy_agent,
    "agriculture": create_agriculture_agent,
    "minerals": create_minerals_agent,
    "digital": create_digital_agent,
    "protocol": create_protocol_agent,
    "resource_mobilization": create_resource_mobilization_agent,
}


def print_welcome(agent_id: str):
    """Print welcome message"""
    print("\n" + "="*70)
    print(f"  ECOWAS Summit 2026 - AI Agent Chat Interface")
    print(f"  Agent: {agent_id.upper().replace('_', ' ')}")
    print("="*70)
    print("\nCommands:")
    print("  • Type your message and press Enter to chat")
    print("  • 'quit' or 'exit' - Exit the chat")
    print("  • 'reset' - Clear conversation history")
    print("  • 'info' - Show agent information")
    print("  • 'help' - Show this help message")

    # Add synthesis commands for supervisor
    if agent_id == "supervisor":
        print("\nCross-TWG Synthesis Commands:")
        print("  • 'synthesis:pillar PILLAR' - Generate pillar overview (energy|agriculture|minerals|digital)")
        print("  • 'synthesis:cross PILLAR1 PILLAR2' - Generate cross-pillar synthesis")
        print("  • 'synthesis:priorities' - Generate strategic priorities across all TWGs")
        print("  • 'synthesis:coherence' - Check policy coherence")
        print("  • 'synthesis:readiness' - Assess summit readiness")

        print("\nDocument Synthesis Commands:")
        print("  • 'document:declaration' - Synthesize Declaration from all TWG sections")
        print("  • 'document:status' - Show document synthesis statistics")

        print("\nScheduling Commands:")
        print("  • 'schedule:view' - View global schedule")
        print("  • 'schedule:conflicts' - Detect scheduling conflicts")
        print("  • 'schedule:summary' - Show scheduling summary")

    print("\n" + "-"*70 + "\n")


def print_info(agent):
    """Print agent information"""
    info = agent.get_agent_info()
    print("\n" + "="*70)
    print("AGENT INFORMATION")
    print("="*70)
    print(f"Agent ID: {info['agent_id']}")
    print(f"History Enabled: {info['keep_history']}")
    print(f"Max History: {info['max_history']}")
    print(f"Current History Length: {info['history_length']}")

    # Show Redis info if available
    if hasattr(agent, 'use_redis'):
        print(f"\nRedis Memory:")
        print(f"  Enabled: {agent.use_redis}")
        if agent.use_redis:
            print(f"  Session ID: {agent.session_id}")
            print(f"  TTL: {agent.memory_ttl or 'default (24h)'}")
            if hasattr(agent, 'redis_memory') and agent.redis_memory:
                health = agent.redis_memory.health_check()
                print(f"  Connection: {'✓ Healthy' if health else '✗ Failed'}")

    print(f"\nSystem Prompt Preview:")
    print(f"{info['system_prompt']}")
    print("="*70 + "\n")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Interactive chat with ECOWAS Summit AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available agents:
  supervisor           - Central coordinator for all TWGs
  energy              - Energy & Infrastructure expert
  agriculture         - Agriculture & Food Systems expert
  minerals            - Critical Minerals & Industrialization expert
  digital             - Digital Economy & Transformation expert
  protocol            - Protocol & Logistics coordinator
  resource_mobilization - Resource Mobilization coordinator

Examples:
  python scripts/chat_agent.py --agent supervisor
  python scripts/chat_agent.py --agent energy --no-history
        """
    )

    parser.add_argument(
        "--agent",
        type=str,
        required=True,
        choices=list(AGENT_FACTORY.keys()),
        help="Agent to chat with"
    )

    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Disable conversation history"
    )

    parser.add_argument(
        "--no-redis",
        action="store_true",
        help="Disable Redis memory (use in-memory only)"
    )

    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Session ID for Redis memory (default: auto-generated)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Configure logging
    if not args.debug:
        logger.remove()
        logger.add(sys.stderr, level="WARNING")

    # Generate session ID if not provided
    import uuid
    session_id = args.session_id or f"cli-{uuid.uuid4().hex[:8]}"

    # Create agent
    try:
        print(f"\nInitializing {args.agent} agent...")

        # Create with Redis support if not disabled
        use_redis = not args.no_redis

        if args.agent == "supervisor":
            agent = AGENT_FACTORY[args.agent](
                keep_history=not args.no_history,
                session_id=session_id,
                use_redis=use_redis,
                memory_ttl=3600  # 1 hour for CLI sessions
            )
        else:
            # Other agents (they'll need similar updates to their factory functions)
            agent = AGENT_FACTORY[args.agent](keep_history=not args.no_history)

        print("✓ Agent initialized successfully!")

        # Show Redis status
        if use_redis:
            print(f"✓ Redis memory enabled (Session: {session_id})")
            if hasattr(agent, 'redis_memory') and agent.redis_memory:
                if agent.redis_memory.health_check():
                    print("✓ Redis connection healthy")
                else:
                    print("⚠️  Redis connection failed - using in-memory fallback")
        else:
            print("ℹ️  Using in-memory storage (use --no-redis to change)")

        # If supervisor, show registered agents
        if args.agent == "supervisor" and hasattr(agent, 'get_supervisor_status'):
            status = agent.get_supervisor_status()
            if status['delegation_enabled']:
                print(f"✓ Supervisor has {status['agent_count']} TWG agents registered:")
                for twg in status['registered_agents']:
                    print(f"  - {twg}")

        # Check LLM connection
        print("\nChecking Ollama connection...")
        if not agent.llm.check_connection():
            print("\n❌ ERROR: Cannot connect to Ollama!")
            print("\nPlease ensure:")
            print("  1. Ollama is installed: https://ollama.ai")
            print("  2. Ollama is running: ollama serve")
            print("  3. Model is pulled: ollama pull qwen2.5:0.5b")
            sys.exit(1)
        print("✓ Ollama connection successful!\n")

    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize agent: {e}")
        sys.exit(1)

    # Print welcome
    print_welcome(args.agent)

    # Chat loop
    try:
        while True:
            # Get user input
            try:
                user_input = input(f"\033[94mYou:\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye!")
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["quit", "exit"]:
                print("\nGoodbye!")
                break

            elif user_input.lower() == "reset":
                agent.reset_history()
                print("\n✓ Conversation history cleared.\n")
                continue

            elif user_input.lower() == "info":
                print_info(agent)
                continue

            elif user_input.lower() == "help":
                print_welcome(args.agent)
                continue

            # Handle synthesis commands (supervisor only)
            elif args.agent == "supervisor" and user_input.lower().startswith("synthesis:"):
                try:
                    parts = user_input.split()
                    command = parts[0].lower()

                    if command == "synthesis:pillar" and len(parts) >= 2:
                        pillar = parts[1].lower()
                        valid_pillars = ["energy", "agriculture", "minerals", "digital"]
                        if pillar not in valid_pillars:
                            print(f"\n❌ Invalid pillar. Choose from: {', '.join(valid_pillars)}\n")
                            continue

                        print(f"\n🔄 Generating {pillar.title()} pillar overview...\n")
                        response = agent.generate_pillar_overview(pillar)
                        print(response)
                        print()

                    elif command == "synthesis:cross" and len(parts) >= 3:
                        pillars = [p.lower() for p in parts[1:]]
                        valid_pillars = ["energy", "agriculture", "minerals", "digital"]

                        invalid = [p for p in pillars if p not in valid_pillars]
                        if invalid:
                            print(f"\n❌ Invalid pillars: {invalid}\n")
                            print(f"Choose from: {', '.join(valid_pillars)}\n")
                            continue

                        print(f"\n🔄 Generating cross-pillar synthesis for {' & '.join(pillars)}...\n")
                        response = agent.generate_cross_pillar_synthesis(pillars)
                        print(response)
                        print()

                    elif command == "synthesis:priorities":
                        print("\n🔄 Generating strategic priorities synthesis...\n")
                        print("⏳ This may take 30-60 seconds (querying all TWGs)...\n")
                        response = agent.generate_strategic_priorities()
                        print(response)
                        print()

                    elif command == "synthesis:coherence":
                        print("\n🔄 Generating policy coherence check...\n")
                        print("⏳ This may take 30-60 seconds (querying all TWGs)...\n")
                        response = agent.generate_policy_coherence_check()
                        print(response)
                        print()

                    elif command == "synthesis:readiness":
                        print("\n🔄 Generating summit readiness assessment...\n")
                        print("⏳ This may take 30-60 seconds (querying all TWGs)...\n")
                        response = agent.generate_summit_readiness_assessment()
                        print(response)
                        print()

                    else:
                        print("\n❌ Invalid synthesis command. Type 'help' to see available commands.\n")

                except Exception as e:
                    print(f"\n❌ Synthesis error: {e}\n")

                continue

            # Handle document synthesis commands (supervisor only)
            elif args.agent == "supervisor" and user_input.lower().startswith("document:"):
                try:
                    command = user_input.lower().strip()

                    if command == "document:declaration":
                        print("\n📄 Synthesizing Declaration from all TWG sections...\n")
                        print("⏳ This may take 1-2 minutes (collecting from all TWGs)...\n")

                        result = agent.synthesize_declaration(
                            title="ECOWAS Summit 2026 Declaration",
                            collect_from_twgs=True
                        )

                        print("=" * 70)
                        print("DECLARATION SYNTHESIS RESULTS")
                        print("=" * 70)
                        print(f"Title: {result['metadata']['title']}")
                        print(f"Word count: {result['metadata']['word_count']}")
                        print(f"Sections: {len(result['metadata']['sections'])}")
                        print(f"Coherence score: {result['metadata']['coherence_score']:.1%}")
                        print(f"\nTerminology changes: {result['synthesis_log']['terminology_changes']}")
                        print(f"Voice adjustments: {result['synthesis_log']['voice_adjustments']}")
                        print(f"Citations added: {result['synthesis_log']['citations_added']}")

                        if result['metadata']['issues']:
                            print(f"\n⚠️  Issues detected ({len(result['metadata']['issues'])}):")
                            for issue in result['metadata']['issues']:
                                print(f"  - {issue}")
                        else:
                            print("\n✓ No coherence issues detected")

                        print("\n" + "-" * 70)
                        print("DECLARATION PREVIEW (first 1000 characters):")
                        print("-" * 70)
                        print(result['document'][:1000])
                        if len(result['document']) > 1000:
                            print("\n... (truncated)")
                        print("-" * 70)

                        # Ask if user wants to save
                        save = input("\nSave full Declaration to file? (y/n): ").strip().lower()
                        if save == 'y':
                            filename = input("Filename (default: declaration_draft.md): ").strip()
                            if not filename:
                                filename = "declaration_draft.md"

                            with open(filename, 'w') as f:
                                f.write(result['document'])
                            print(f"\n✓ Declaration saved to: {filename}\n")

                    elif command == "document:status":
                        print("\n📊 Document Synthesis Statistics\n")

                        history = agent.document_synthesizer.get_synthesis_history()

                        if not history:
                            print("No documents synthesized yet.\n")
                        else:
                            print(f"Total documents synthesized: {len(history)}\n")

                            for i, doc in enumerate(history, 1):
                                print(f"{i}. {doc['metadata']['title']}")
                                print(f"   Words: {doc['metadata']['word_count']}")
                                print(f"   Coherence: {doc['metadata']['coherence_score']:.1%}")
                                print(f"   Sections: {len(doc['metadata']['sections'])}")
                                print(f"   Synthesized: {doc['metadata']['synthesized_at']}")
                                print()

                        # Show terminology standards
                        standards = agent.document_synthesizer.get_terminology_standards()
                        if standards:
                            print("Terminology Standards:")
                            for twg_id, terms in standards.items():
                                print(f"  {twg_id.upper()}:")
                                for abbr, full in terms.items():
                                    print(f"    {abbr} → {full}")
                            print()

                    else:
                        print("\n❌ Invalid document command. Type 'help' to see available commands.\n")

                except Exception as e:
                    print(f"\n❌ Document synthesis error: {e}\n")
                    import traceback
                    traceback.print_exc()

                continue

            # Handle scheduling commands (supervisor only)
            elif args.agent == "supervisor" and user_input.lower().startswith("schedule:"):
                try:
                    command = user_input.lower().strip()

                    if command == "schedule:view":
                        print("\n📅 Global Schedule\n")

                        schedule = agent.get_global_schedule()

                        if not schedule:
                            print("No events scheduled yet.\n")
                        else:
                            print(f"Total events: {len(schedule)}\n")

                            from collections import defaultdict
                            by_day = defaultdict(list)

                            for event in schedule:
                                day = event.start_time.date()
                                by_day[day].append(event)

                            for day, events in sorted(by_day.items()):
                                print(f"\n{day.strftime('%B %d, %Y')}:")
                                print("-" * 50)
                                for event in events:
                                    print(f"{event.start_time.strftime('%H:%M')} - {event.end_time.strftime('%H:%M')}")
                                    print(f"  {event.title}")
                                    print(f"  Type: {event.event_type.value}, Priority: {event.priority.value}")
                                    print(f"  TWGs: {', '.join(event.required_twgs)}")
                                    if event.vip_attendees:
                                        print(f"  VIPs: {', '.join(event.vip_attendees)}")
                                    print()

                    elif command == "schedule:conflicts":
                        print("\n⚠️  Detecting Scheduling Conflicts...\n")

                        conflicts = agent.detect_schedule_conflicts()

                        if not conflicts:
                            print("✓ No scheduling conflicts detected.\n")
                        else:
                            print(f"Found {len(conflicts)} conflicts:\n")

                            for i, conflict in enumerate(conflicts, 1):
                                print(f"Conflict #{i}:")
                                print(f"  Type: {conflict.conflict_type}")
                                print(f"  Severity: {conflict.severity.upper()}")
                                print(f"  Events: {', '.join(conflict.event_titles)}")
                                print(f"  Description: {conflict.description}")
                                print(f"  Impact: {conflict.impact}")
                                if conflict.suggested_resolution:
                                    print(f"  Suggestion: {conflict.suggested_resolution}")
                                print()

                    elif command == "schedule:summary":
                        print("\n📊 Scheduling Summary\n")

                        summary = agent.get_scheduling_summary()

                        print(f"Total events: {summary['total_events']}")
                        print(f"\nBy Type:")
                        for event_type, count in summary['by_type'].items():
                            print(f"  {event_type}: {count}")

                        print(f"\nBy Priority:")
                        for priority, count in summary['by_priority'].items():
                            print(f"  {priority}: {count}")

                        print(f"\nBy Status:")
                        for status, count in summary['by_status'].items():
                            print(f"  {status}: {count}")

                        print(f"\nConflicts:")
                        print(f"  Total: {summary['total_conflicts']}")
                        print(f"  Critical: {summary['critical_conflicts']}")
                        print()

                    else:
                        print("\n❌ Invalid schedule command. Type 'help' to see available commands.\n")

                except Exception as e:
                    print(f"\n❌ Scheduling error: {e}\n")
                    import traceback
                    traceback.print_exc()

                continue

            # Send to agent
            try:
                print(f"\033[92m{args.agent.title()}:\033[0m ", end="", flush=True)

                # Use chat_with_tools for supervisor (async), smart_chat or regular chat for others
                if args.agent == "supervisor" and hasattr(agent, 'chat_with_tools'):
                    response = asyncio.run(agent.chat_with_tools(user_input))
                elif args.agent == "supervisor" and hasattr(agent, 'smart_chat'):
                    response = agent.smart_chat(user_input)
                else:
                    response = agent.chat(user_input)

                print(response)
                print()  # Empty line for readability

            except Exception as e:
                print(f"\n❌ Error: {e}\n")

    except KeyboardInterrupt:
        print("\n\nGoodbye!")

    finally:
        print("\nThank you for using the ECOWAS Summit AI Agent System!\n")


if __name__ == "__main__":
    main()
