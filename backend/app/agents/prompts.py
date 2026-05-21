"""
System Prompts for All AI Agents

Each agent has its own prompt file in the prompts/ directory.
This module provides a unified interface to load agent prompts.
"""

from pathlib import Path
from typing import Dict


# Cache for loaded prompts (Reload triggered for prompt updates - Content Filter & Drafting Fix)
_PROMPT_CACHE: Dict[str, str] = {}

# Available agent IDs
AVAILABLE_AGENTS = [
    "supervisor",
    "energy",
    "agriculture",
    "minerals",
    "digital",
    "protocol",
    "resource_mobilization"
]


def get_prompt(agent_id: str) -> str:
    """
    Get the system prompt for a specific agent.
    For 'supervisor', appends platform_guide.txt if present.
    """
    if agent_id not in AVAILABLE_AGENTS:
        available = ", ".join(AVAILABLE_AGENTS)
        raise ValueError(
            f"Unknown agent_id: '{agent_id}'. "
            f"Available agents: {available}"
        )

    if agent_id in _PROMPT_CACHE:
        return _PROMPT_CACHE[agent_id]

    prompts_dir = Path(__file__).parent / "prompts"
    prompt_file = prompts_dir / f"{agent_id}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found for agent '{agent_id}': {prompt_file}"
        )

    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt = f.read().strip()

    if agent_id == "supervisor":
        guide_file = prompts_dir / "platform_guide.txt"
        if guide_file.exists():
            with open(guide_file, 'r', encoding='utf-8') as f:
                guide = f.read().strip()
            prompt = prompt + "\n\n" + guide

    _PROMPT_CACHE[agent_id] = prompt
    return prompt


def list_agents() -> list:
    """
    Get list of all available agent IDs.

    Returns:
        list: List of agent identifiers

    Example:
        >>> agents = list_agents()
        >>> print(agents)
        ['supervisor', 'energy', 'agriculture', ...]
    """
    return AVAILABLE_AGENTS.copy()


def reload_prompts() -> None:
    """
    Clear the prompt cache to force reload from files.

    Useful during development when prompt files are being modified.

    Example:
        >>> reload_prompts()  # Clear cache
        >>> prompt = get_prompt("energy")  # Loads fresh from file
    """
    global _PROMPT_CACHE
    _PROMPT_CACHE.clear()


def get_all_prompts() -> Dict[str, str]:
    """
    Load all agent prompts into a dictionary.

    Returns:
        Dict[str, str]: Dictionary mapping agent_id to prompt

    Example:
        >>> prompts = get_all_prompts()
        >>> print(prompts.keys())
        dict_keys(['supervisor', 'energy', 'agriculture', ...])
    """
    return {agent_id: get_prompt(agent_id) for agent_id in AVAILABLE_AGENTS}
