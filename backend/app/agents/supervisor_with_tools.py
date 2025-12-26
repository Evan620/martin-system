"""
Supervisor Agent with Tool Execution

Extends the base Supervisor with the ability to detect and execute email tool calls
from LLM responses, even without native function calling support.
"""

import re
import asyncio
import json
from typing import Dict, Any, Optional
from loguru import logger

from app.agents.supervisor import SupervisorAgent


class SupervisorWithTools(SupervisorAgent):
    """
    Enhanced Supervisor that can execute email tools based on LLM responses.

    This wrapper intercepts the chat response and looks for tool call patterns,
    then executes the appropriate email tools automatically.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_execution_enabled = True

    async def chat_with_tools(self, message: str, temperature: Optional[float] = None) -> str:
        """
        Enhanced chat that detects email requests and executes tools automatically.

        This method uses pattern matching to detect when the user is asking for email operations
        and executes the appropriate tools before getting the LLM response.

        Args:
            message: User message
            temperature: Optional temperature override

        Returns:
            Response with tool results integrated
        """
        if not self.tool_execution_enabled:
            return self.chat(message, temperature)

        # Detect if this is an email-related request
        tool_call = self._detect_email_request(message)

        if tool_call:
            logger.info(f"Detected email request: {tool_call['tool']} with args {tool_call['args']}")

            try:
                # Execute the tool
                result = await self._execute_tool(tool_call['tool'], tool_call['args'])

                # Format the result for the user
                if result.get('status') == 'success':
                    if tool_call['tool'] == 'search_emails':
                        # Format email search results
                        emails = result.get('emails', [])
                        count = result.get('count', 0)

                        if count == 0:
                            return "I checked your Gmail but found no emails matching that criteria."

                        response = f"I found {count} email(s) in your Gmail:\n\n"
                        for i, email in enumerate(emails[:10], 1):  # Show max 10
                            response += f"{i}. **{email['subject']}**\n"
                            response += f"   From: {email['from']}\n"
                            response += f"   Date: {email['date']}\n"
                            response += f"   Preview: {email['snippet'][:100]}...\n\n"

                        if count > 10:
                            response += f"\n... and {count - 10} more emails."

                        return response

                    elif tool_call['tool'] in ['send_email', 'send_notification_email', 'send_meeting_summary_email', 'send_report_email']:
                        return f"Email sent successfully! Message ID: {result.get('message_id')}"

                    elif tool_call['tool'] == 'broadcast_email_to_all_twgs':
                        successful = sum(1 for r in result.values() if r.get('status') == 'success')
                        total = len(result)
                        return f"Broadcast complete! Successfully sent to {successful}/{total} TWGs."

                    elif tool_call['tool'] == 'get_email_tools_status':
                        tools = result.get('available_tools', [])
                        return f"Email tools are available. {len(tools)} tools ready: {', '.join(tools)}"

                else:
                    return f"Error executing email tool: {result.get('error', 'Unknown error')}"

            except Exception as e:
                logger.error(f"Error executing tool: {e}")
                return f"I encountered an error while trying to access Gmail: {str(e)}"

        # No tool detected, use regular chat
        return self.chat(message, temperature)

    def _detect_email_request(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Detect if the message is requesting an email operation.

        Args:
            message: User message

        Returns:
            Dict with tool name and args, or None
        """
        message_lower = message.lower()

        # Pattern 1: Search/Check emails
        if any(keyword in message_lower for keyword in ['check email', 'search email', 'find email', 'last email', 'recent email', 'show email', 'get email', 'list email', 'my email']):
            # Extract parameters
            max_results = 5  # default

            # Check for number of emails requested
            number_match = re.search(r'last\s+(\d+)', message_lower)
            if number_match:
                max_results = int(number_match.group(1))
            elif 'all' in message_lower:
                max_results = 50

            # Determine query
            query = "is:inbox"  # default

            if 'unread' in message_lower:
                query = "is:unread"
            elif any(word in message_lower for word in ['from:', 'subject:', 'to:']):
                # User specified a query
                query = message_lower  # Use the whole message as query

            return {
                'tool': 'search_emails',
                'args': {
                    'query': query,
                    'max_results': max_results,
                    'include_body': False
                }
            }

        # Pattern 2: Send email
        elif any(keyword in message_lower for keyword in ['send email', 'email to', 'send mail', 'compose email', 'send a', 'send demo', 'send report', 'send notification']):
            # Extract email address
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            email_match = re.search(email_pattern, message)

            if email_match:
                recipient_email = email_match.group(0)

                # Determine email type and create appropriate content
                if 'report' in message_lower or 'demo report' in message_lower:
                    # Send a demo report
                    return {
                        'tool': 'send_report_email',
                        'args': {
                            'to': recipient_email,
                            'report_data': {
                                'title': 'ECOWAS Summit 2026 - Demo Report',
                                'summary': 'This is a demonstration report from the ECOWAS Summit TWG Support System.',
                                'metrics': [
                                    {'label': 'Active TWGs', 'value': '6', 'trend': '+100%'},
                                    {'label': 'Policy Documents', 'value': '24', 'trend': '+50%'},
                                    {'label': 'Stakeholder Engagement', 'value': '89%', 'trend': '+12%'}
                                ],
                                'sections': [
                                    {
                                        'title': 'Executive Summary',
                                        'content': 'The ECOWAS Summit 2026 TWG Support System is operational with 6 active Technical Working Groups coordinating across Energy Transition, Mineral Industrialization, Agriculture & Food Security, and Digital Economy pillars.'
                                    },
                                    {
                                        'title': 'Key Achievements',
                                        'content': 'Successfully deployed AI-powered coordination system, established cross-TWG communication protocols, and initiated policy synthesis workflows.'
                                    },
                                    {
                                        'title': 'Next Steps',
                                        'content': 'Continue policy development, enhance stakeholder engagement, and prepare deliverables for the Abuja Declaration and Freetown Communiqué.'
                                    }
                                ]
                            },
                            'subject': 'ECOWAS Summit 2026 - Demo Report',
                            'cc': None
                        }
                    }
                elif 'meeting' in message_lower or 'summary' in message_lower:
                    # Send a demo meeting summary
                    return {
                        'tool': 'send_meeting_summary_email',
                        'args': {
                            'to': recipient_email,
                            'meeting_data': {
                                'meeting_title': 'ECOWAS Summit TWG Coordination Meeting',
                                'date': '2025-12-26',
                                'attendees': ['Energy TWG', 'Agriculture TWG', 'Minerals TWG', 'Digital TWG', 'Protocol TWG', 'Resource Mobilization TWG'],
                                'summary': 'Discussed cross-TWG coordination for ECOWAS Summit 2026 deliverables and reviewed progress on policy synthesis.',
                                'action_items': [
                                    {'task': 'Finalize energy transition roadmap', 'assignee': 'Energy TWG', 'due_date': '2026-01-15'},
                                    {'task': 'Complete agriculture policy synthesis', 'assignee': 'Agriculture TWG', 'due_date': '2026-01-20'},
                                    {'task': 'Review mineral industrialization framework', 'assignee': 'Minerals TWG', 'due_date': '2026-01-18'}
                                ],
                                'next_meeting': '2026-01-10 10:00 AM'
                            },
                            'cc': None
                        }
                    }
                elif 'notification' in message_lower or 'alert' in message_lower:
                    # Send a demo notification
                    return {
                        'tool': 'send_notification_email',
                        'args': {
                            'to': recipient_email,
                            'heading': 'ECOWAS Summit 2026 - System Notification',
                            'message': 'This is a demonstration notification from the ECOWAS Summit TWG Support System.',
                            'subject': 'ECOWAS Summit - Demo Notification',
                            'details': 'The AI-powered coordination system is now operational and ready to support all Technical Working Groups.',
                            'action_url': 'https://ecowas-summit-2026.org',
                            'action_text': 'Visit Summit Portal',
                            'cc': None
                        }
                    }
                else:
                    # Generic email with demo content
                    return {
                        'tool': 'send_email',
                        'args': {
                            'to': recipient_email,
                            'subject': 'ECOWAS Summit 2026 - Demo Email',
                            'message': 'This is a demonstration email from the ECOWAS Summit TWG Support System.',
                            'html_body': '<h1>ECOWAS Summit 2026</h1><p>This is a demonstration email from the TWG Support System.</p><p>The system is operational and ready to assist with coordination across all Technical Working Groups.</p>',
                            'cc': None,
                            'bcc': None,
                            'attachments': None
                        }
                    }

            # If no email address found, return None to let LLM handle it
            return None

        # Pattern 3: Email tools status
        elif any(keyword in message_lower for keyword in ['email tools', 'email capability', 'email features', 'can you email']):
            return {
                'tool': 'get_email_tools_status',
                'args': {}
            }

        return None

    async def _execute_tool_calls_from_response(self, response: str) -> list:
        """
        Parse and execute tool calls from LLM response.

        Args:
            response: LLM response containing TOOL_CALL statements

        Returns:
            List of tool execution results
        """
        results = []

        # Find all tool calls in the response
        tool_call_pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)'
        matches = re.findall(tool_call_pattern, response, re.MULTILINE)

        for tool_name, args_str in matches:
            try:
                logger.info(f"Executing tool: {tool_name} with args: {args_str}")

                # Parse arguments
                args = self._parse_tool_arguments(args_str)

                # Execute the tool
                result = await self._execute_tool(tool_name, args)

                results.append({
                    'tool': tool_name,
                    'args': args,
                    'result': result
                })

                logger.info(f"Tool {tool_name} executed successfully")

            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                results.append({
                    'tool': tool_name,
                    'args': args_str,
                    'result': {'status': 'error', 'error': str(e)}
                })

        return results

    def _parse_tool_arguments(self, args_str: str) -> Dict[str, Any]:
        """
        Parse tool arguments from string format.

        Args:
            args_str: Argument string like 'query="is:unread", max_results=5'

        Returns:
            Dictionary of parsed arguments
        """
        args = {}

        # Simple parser for key=value pairs
        # Handle both quoted and unquoted values
        arg_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|(\d+)|(\w+))'
        matches = re.findall(arg_pattern, args_str)

        for match in matches:
            key = match[0]
            # Get the first non-empty value (quoted string, number, or word)
            value = match[1] or match[2] or match[3]

            # Convert numbers
            if value.isdigit():
                value = int(value)
            # Convert booleans
            elif value.lower() in ('true', 'false'):
                value = value.lower() == 'true'

            args[key] = value

        return args

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a specific email tool.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool execution result
        """
        # Map of available tools
        tool_map = {
            'search_emails': self.search_emails,
            'send_email': self.send_email,
            'send_meeting_summary_email': self.send_meeting_summary_email,
            'send_report_email': self.send_report_email,
            'send_notification_email': self.send_notification_email,
            'broadcast_email_to_all_twgs': self.broadcast_email_to_all_twgs,
            'get_email_tools_status': self.get_email_tools_status,
        }

        if tool_name not in tool_map:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool_func = tool_map[tool_name]

        # Execute the tool
        result = await tool_func(**args)

        return result

    def enable_tool_execution(self, enabled: bool = True):
        """Enable or disable automatic tool execution."""
        self.tool_execution_enabled = enabled
        logger.info(f"Tool execution {'enabled' if enabled else 'disabled'}")


def create_supervisor_with_tools(
    keep_history: bool = True,
    auto_register: bool = True,
    session_id: Optional[str] = None,
    use_redis: bool = False,
    memory_ttl: Optional[int] = None
) -> SupervisorWithTools:
    """
    Create a Supervisor agent with tool execution capabilities.

    Args:
        keep_history: Whether to maintain conversation history
        auto_register: If True, automatically register all TWG agents
        session_id: Session identifier for Redis memory (optional)
        use_redis: If True, use Redis for persistent memory
        memory_ttl: TTL for Redis keys in seconds (optional)

    Returns:
        SupervisorWithTools instance
    """
    supervisor = SupervisorWithTools(
        keep_history=keep_history,
        session_id=session_id,
        use_redis=use_redis,
        memory_ttl=memory_ttl
    )

    if auto_register:
        supervisor.register_all_agents()

    return supervisor
