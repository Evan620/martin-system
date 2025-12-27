"""
Command Parser Service

Parses user messages for slash commands and @mentions, enabling
a powerful command-driven chat interface.

Supports:
- Slash commands: /email, /search, /schedule, /draft, /analyze, /broadcast
- @mentions: @EnergyAgent, @AgricultureAgent, etc.
- Command parameters: /email send to:user@example.com subject:Test
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class MessageParseType(str, Enum):
    """Types of parsed messages."""
    COMMAND = "command"
    MENTION = "mention"
    MIXED = "mixed"  # Contains both command and mentions
    NATURAL = "natural"  # Regular natural language


class CommandParser:
    """Parse slash commands and @mentions from user input."""

    # Available slash commands
    COMMANDS = {
        "/email": {
            "handler": "handle_email_command",
            "description": "Send emails or search inbox",
            "category": "communication",
            "examples": [
                "/email search unread",
                "/email send to:user@example.com subject:Meeting",
                "/email to:team@ecowas.int cc:admin@ecowas.int subject:Update body:Here is the update"
            ],
            "parameters": ["to", "cc", "subject", "body", "search"]
        },
        "/search": {
            "handler": "handle_search_command",
            "description": "Search knowledge base",
            "category": "analysis",
            "examples": [
                "/search energy policy",
                "/search renewable targets 2026",
                "/search @EnergyAgent solar initiatives"
            ],
            "parameters": ["query"]
        },
        "/schedule": {
            "handler": "handle_schedule_command",
            "description": "Check schedules or create meetings",
            "category": "meetings",
            "examples": [
                "/schedule check energy",
                "/schedule meeting tomorrow 2pm",
                "/schedule list next week"
            ],
            "parameters": ["action", "date", "time", "twg"]
        },
        "/draft": {
            "handler": "handle_draft_command",
            "description": "Draft documents",
            "category": "documents",
            "examples": [
                "/draft minutes",
                "/draft agenda for energy meeting",
                "/draft policy brief on renewable energy"
            ],
            "parameters": ["type", "topic"]
        },
        "/analyze": {
            "handler": "handle_analyze_command",
            "description": "Analyze documents or data",
            "category": "analysis",
            "examples": [
                "/analyze last 3 meetings",
                "/analyze energy trends",
                "/analyze @EnergyAgent progress"
            ],
            "parameters": ["scope", "target"]
        },
        "/broadcast": {
            "handler": "handle_broadcast_command",
            "description": "Broadcast to all TWGs",
            "category": "communication",
            "examples": [
                "/broadcast urgent update on summit dates",
                "/broadcast reminder for next meeting"
            ],
            "parameters": ["message"]
        },
        "/summarize": {
            "handler": "handle_summarize_command",
            "description": "Summarize meetings or documents",
            "category": "analysis",
            "examples": [
                "/summarize last meeting",
                "/summarize energy twg meetings this month"
            ],
            "parameters": ["target", "scope"]
        }
    }

    # TWG agent mentions
    AGENT_MENTIONS = {
        "@EnergyAgent": {
            "agent_id": "energy",
            "name": "Energy & Infrastructure TWG Agent",
            "icon": "bolt",
            "description": "Handles energy transition, renewable targets, and infrastructure"
        },
        "@AgricultureAgent": {
            "agent_id": "agriculture",
            "name": "Agriculture & Food Security TWG Agent",
            "icon": "agriculture",
            "description": "Handles food security, agricultural development"
        },
        "@MineralsAgent": {
            "agent_id": "minerals",
            "name": "Mineral Industrialization TWG Agent",
            "icon": "science",
            "description": "Handles mineral resources, industrialization"
        },
        "@DigitalAgent": {
            "agent_id": "digital",
            "name": "Digital Economy TWG Agent",
            "icon": "computer",
            "description": "Handles digital transformation, technology"
        },
        "@ProtocolAgent": {
            "agent_id": "protocol",
            "name": "Protocol & Procedures TWG Agent",
            "icon": "gavel",
            "description": "Handles summit protocol, procedures"
        },
        "@ResourceAgent": {
            "agent_id": "resource_mobilization",
            "name": "Resource Mobilization TWG Agent",
            "icon": "account_balance",
            "description": "Handles funding, resource allocation"
        }
    }

    def parse_message(self, message: str) -> Dict[str, Any]:
        """
        Parse user message for commands and mentions.

        Args:
            message: Raw user message

        Returns:
            Dictionary with parsing results:
            {
                "type": MessageParseType,
                "command": Optional[str],  # Command name if found
                "agent_mentions": List[str],  # List of mentioned agent IDs
                "clean_query": str,  # Message with commands/mentions removed
                "raw_message": str,  # Original message
                "parameters": Dict[str, str]  # Extracted command parameters
            }
        """
        result = {
            "type": MessageParseType.NATURAL,
            "command": None,
            "agent_mentions": [],
            "clean_query": message,
            "raw_message": message,
            "parameters": {}
        }

        # Check for slash commands
        command_match = self._extract_command(message)
        if command_match:
            result["command"] = command_match["command"]
            result["parameters"] = command_match["parameters"]
            result["clean_query"] = command_match["remaining_text"]

        # Check for @mentions
        mentions = self._extract_mentions(message)
        if mentions:
            result["agent_mentions"] = mentions["agent_ids"]
            # Remove mentions from clean query
            clean = result["clean_query"]
            for mention in mentions["mentions"]:
                clean = clean.replace(mention, "").strip()
            result["clean_query"] = clean

        # Determine message type
        if result["command"] and result["agent_mentions"]:
            result["type"] = MessageParseType.MIXED
        elif result["command"]:
            result["type"] = MessageParseType.COMMAND
        elif result["agent_mentions"]:
            result["type"] = MessageParseType.MENTION

        return result

    def _extract_command(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract slash command and parameters from message."""
        # Match commands at start of message or after whitespace
        pattern = r'(?:^|\s)(\/\w+)'
        match = re.search(pattern, message)

        if not match:
            return None

        command = match.group(1).lower()

        if command not in self.COMMANDS:
            return None

        # Extract parameters (key:value pairs)
        param_pattern = r'(\w+):([^\s]+)'
        params = dict(re.findall(param_pattern, message))

        # Get remaining text after removing command and parameters
        remaining = message.replace(command, "", 1)
        for key, value in params.items():
            remaining = remaining.replace(f"{key}:{value}", "")
        remaining = remaining.strip()

        # If no key:value params, treat remaining text as the main parameter
        if not params and remaining:
            # Get expected parameters for this command
            expected = self.COMMANDS[command].get("parameters", [])
            if expected:
                # Use first parameter as default
                params[expected[0]] = remaining

        return {
            "command": command,
            "parameters": params,
            "remaining_text": remaining
        }

    def _extract_mentions(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract @mentions from message."""
        mentions = []
        agent_ids = []

        for mention, config in self.AGENT_MENTIONS.items():
            if mention in message:
                mentions.append(mention)
                agent_ids.append(config["agent_id"])

        if not mentions:
            return None

        return {
            "mentions": mentions,
            "agent_ids": agent_ids
        }

    def extract_command_params(self, command: str, message: str) -> Dict[str, Any]:
        """
        Extract parameters from command string.

        Args:
            command: Command name (e.g., "/email")
            message: Full message text

        Returns:
            Dictionary of extracted parameters
        """
        parse_result = self._extract_command(message)
        if parse_result and parse_result["command"] == command:
            return parse_result["parameters"]
        return {}

    def get_command_suggestions(self, partial: str) -> List[Dict[str, str]]:
        """
        Get command autocomplete suggestions.

        Args:
            partial: Partial command text (e.g., "/em")

        Returns:
            List of matching commands with metadata
        """
        if not partial.startswith("/"):
            return []

        partial_lower = partial.lower()
        suggestions = []

        for command, config in self.COMMANDS.items():
            if command.startswith(partial_lower):
                suggestions.append({
                    "command": command,
                    "description": config["description"],
                    "category": config.get("category", "general"),
                    "examples": config.get("examples", [])[0] if config.get("examples") else "",
                    "match_score": self._calculate_match_score(command, partial_lower)
                })

        # Sort by match score (descending)
        suggestions.sort(key=lambda x: x["match_score"], reverse=True)
        return suggestions

    def get_mention_suggestions(self, partial: str) -> List[Dict[str, str]]:
        """
        Get @mention autocomplete suggestions.

        Args:
            partial: Partial mention text (e.g., "@En")

        Returns:
            List of matching agent mentions
        """
        if not partial.startswith("@"):
            return []

        partial_lower = partial.lower()
        suggestions = []

        for mention, config in self.AGENT_MENTIONS.items():
            if mention.lower().startswith(partial_lower):
                suggestions.append({
                    "mention": mention,
                    "agent_id": config["agent_id"],
                    "name": config["name"],
                    "icon": config.get("icon", "smart_toy"),
                    "description": config.get("description", ""),
                    "match_score": self._calculate_match_score(mention, partial_lower)
                })

        # Sort by match score (descending)
        suggestions.sort(key=lambda x: x["match_score"], reverse=True)
        return suggestions

    def _calculate_match_score(self, text: str, partial: str) -> float:
        """Calculate how well text matches partial input (0-1)."""
        if not partial:
            return 0.0

        text_lower = text.lower()
        partial_lower = partial.lower()

        # Exact prefix match gets highest score
        if text_lower.startswith(partial_lower):
            return len(partial_lower) / len(text_lower)

        # Substring match gets lower score
        if partial_lower in text_lower:
            return 0.5 * (len(partial_lower) / len(text_lower))

        return 0.0

    def get_all_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get all available commands with metadata."""
        return self.COMMANDS.copy()

    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all available agent mentions with metadata."""
        return self.AGENT_MENTIONS.copy()

    def validate_command(self, command: str, parameters: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Validate command and parameters.

        Args:
            command: Command name
            parameters: Command parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        if command not in self.COMMANDS:
            return False, f"Unknown command: {command}"

        config = self.COMMANDS[command]
        expected_params = config.get("parameters", [])

        # Check for required parameters (first parameter is usually required)
        if expected_params and not parameters:
            return False, f"Command {command} requires parameters: {', '.join(expected_params)}"

        return True, None
