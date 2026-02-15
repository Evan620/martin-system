"""
Intent Parser for Natural Language Directives

This module provides the `IntentParser` class which uses an LLM to extract
structured intent from unstructured human directives.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
from loguru import logger

from app.services.llm_service import get_llm_service


class DirectiveIntent(BaseModel):
    """Structured intent extracted from a human directive."""
    
    primary_action: str = Field(
        ..., 
        description="The primary action required (schedule, draft, review, notify, resolve, synthesize, unknown)"
    )
    
    target_twgs: List[str] = Field(
        ..., 
        description="List of target TWGs (e.g., 'energy', 'agriculture') or ['ALL']"
    )
    
    task_type: str = Field(
        ...,
        description="Specific task type (e.g., 'policy_draft', 'meeting_schedule', 'conflict_resolution')"
    )
    
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key parameters for the task (deadline, topic, entities)"
    )
    
    urgency: str = Field(
        "medium",
        description="Urgency level (low, medium, high, critical)"
    )
    
    requires_negotiation: bool = Field(
        False,
        description="True if the directive implies conflict resolution or multi-party negotiation"
    )
    
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of TWGs that are dependencies for this task"
    )


class IntentParser:
    """Uses LLM to parse natural language directives into structured intent."""
    
    def __init__(self):
        self.llm = get_llm_service()
        
    async def parse_directive(self, directive: str, context: Optional[Dict] = None) -> DirectiveIntent:
        """
        Parse a natural language directive using LLM tool use.
        
        Args:
            directive: The unstructured text directive
            context: Optional context dictionary (user role, active TWG, etc.)
            
        Returns:
            DirectiveIntent: The structured intent
        """
        system_prompt = """
        You are the Intent Parser for the ECOWAS Summit Supervisor Agent.
        Your job is to extract structured intent from human directives.
        
        Analyze the directive and extract:
        1. Primary Action: What is the main goal? (schedule, draft, review, notify, resolve, synthesize)
        2. Target TWGs: Which Technical Working Groups are involved? (Available: Energy, Agriculture, Minerals, Digital)
        3. Urgency: Is this critical/immediate or routine?
        4. Negotiation: Does this involve resolving a conflict or dispute?
        
        Examples:
        - "Energy TWG needs to finalize their policy paper by March 1" -> Action: draft, TWG: Energy, Params: {deadline: "2026-03-01"}
        - "Schedule a workshop between Minerals and Digital on batteries" -> Action: schedule, TWGs: [Minerals, Digital], Params: {topic: "batteries"}
        - "Resolve the conflict between Ag and Energy regarding water use" -> Action: resolve, TWGs: [Agriculture, Energy], Negotiation: True
        """
        
        # Define the tool (function definition)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "extract_intent",
                    "description": "Extract structured intent from a directive",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "primary_action": {
                                "type": "string",
                                "enum": ["schedule", "draft", "review", "notify", "resolve", "synthesize", "unknown"],
                                "description": "The primary action required"
                            },
                            "target_twgs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of target TWGs (lowercase)"
                            },
                            "task_type": {
                                "type": "string",
                                "description": "Specific task type identifier"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Key parameters (deadline, topic, etc.)"
                            },
                            "urgency": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                                "description": "Urgency level"
                            },
                            "requires_negotiation": {
                                "type": "boolean",
                                "description": "Whether negotiation is required"
                            },
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Dependent TWGs"
                            }
                        },
                        "required": ["primary_action", "target_twgs", "task_type", "urgency"]
                    }
                }
            }
        ]
        
        try:
            # Call LLM with tool
            response_msg = self.llm.chat(
                prompt=f"Directive: {directive}\nContext: {context or {}}",
                system_prompt=system_prompt,
                tools=tools,
                temperature=0.1  # Low temperature for deterministic extraction
            )
            
            # Check if tool was called
            if hasattr(response_msg, 'tool_calls') and response_msg.tool_calls:
                tool_call = response_msg.tool_calls[0]
                args = json.loads(tool_call.function.arguments)
                
                logger.info(f"[IntentParser] Extracted intent: {args}")
                return DirectiveIntent(**args)
            
            # Fallback if no tool called (should rarely happen with forced tool choice patterns, 
            # but Groq implementation relies on model steering)
            logger.warning("[IntentParser] LLM did not call tool. Returning 'unknown' intent.")
            return DirectiveIntent(
                primary_action="unknown",
                target_twgs=[],
                task_type="general_query",
                urgency="medium",
                parameters={"raw_response": str(response_msg)}
            )
            
        except Exception as e:
            logger.error(f"[IntentParser] Error parsing directive: {e}")
            # Fail gracefully
            return DirectiveIntent(
                primary_action="unknown",
                target_twgs=[],
                task_type="error",
                urgency="medium",
                parameters={"error": str(e)}
            )

# Global instance
_parser_instance = None

def get_intent_parser() -> IntentParser:
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = IntentParser()
    return _parser_instance
