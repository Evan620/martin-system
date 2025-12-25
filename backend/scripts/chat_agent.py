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

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.agents.supervisor import create_supervisor
from app.agents.energy_agent import create_energy_agent
from app.agents.agriculture_agent import create_agriculture_agent
from app.agents.minerals_agent import create_minerals_agent
from app.agents.digital_agent import create_digital_agent
from app.agents.protocol_agent import create_protocol_agent
from app.agents.resource_mobilization_agent import create_resource_mobilization_agent
from app.agents.prompts import list_agents


# Agent factory mapping
AGENT_FACTORY = {
    "supervisor": create_supervisor,
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

            # Send to agent
            try:
                print(f"\033[92m{args.agent.title()}:\033[0m ", end="", flush=True)

                # Use smart_chat for supervisor if available
                if args.agent == "supervisor" and hasattr(agent, 'smart_chat'):
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
