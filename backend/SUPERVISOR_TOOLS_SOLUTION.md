# Supervisor Email Tools - Solution

## Problem
The Supervisor was rejecting email requests like "what are the last 4 emails in my gmail" because:
1. The system prompt didn't mention email tools
2. The LLM couldn't actually execute the Python async methods

## Solution Implemented

### 1. Updated System Prompt ✅
Added email tools documentation to [prompts/supervisor.txt](app/agents/prompts/supervisor.txt):
- Listed all 7 available email tools
- Provided usage examples
- Explained when to use each tool
- Added Gmail query syntax reference

### 2. Created SupervisorWithTools ✅
New enhanced supervisor in [supervisor_with_tools.py](app/agents/supervisor_with_tools.py):
- **Pattern Matching**: Detects email requests from natural language
- **Auto-Execution**: Executes the appropriate Gmail tool automatically
- **Result Formatting**: Formats tool results in human-readable format
- **Graceful Fallback**: Falls back to regular chat for non-email queries

## How It Works

### Pattern Detection
The `_detect_email_request()` method recognizes patterns like:
- "check email", "last emails", "recent emails" → `search_emails()`
- "unread" → adds `is:unread` to query
- "last 4" → sets `max_results=4`
- "email tools" → `get_email_tools_status()`

### Example Flow
```
User: "what are the last 4 emails in my gmail"
  ↓
Pattern detected: "last" + "4" + "email"
  ↓
Tool call: search_emails(query="is:inbox", max_results=4)
  ↓
Execute Gmail API
  ↓
Format results with subject, from, date, preview
  ↓
Return formatted response to user
```

## Usage

### Option 1: Use SupervisorWithTools (Recommended)
```python
import asyncio
from app.agents.supervisor_with_tools import create_supervisor_with_tools

async def main():
    supervisor = create_supervisor_with_tools()

    # This will automatically detect and execute email tool
    response = await supervisor.chat_with_tools("what are my last 5 emails")
    print(response)

asyncio.run(main())
```

### Option 2: Direct Tool Calls (For Programmatic Use)
```python
import asyncio
from app.agents.supervisor import create_supervisor

async def main():
    supervisor = create_supervisor()

    # Call tools directly
    result = await supervisor.search_emails(
        query="is:unread",
        max_results=10
    )

    print(f"Found {result['count']} unread emails")

asyncio.run(main())
```

## Testing

### Run Test Suite
```bash
cd backend
python test_supervisor_tools.py
```

### Test with Chat Agent
```bash
# Need to update chat_agent.py to use SupervisorWithTools
python scripts/chat_agent.py --agent supervisor
```

Then try:
- "what are the last 4 emails in my gmail"
- "show me unread emails"
- "check my inbox"
- "what email tools do you have"

## Supported Email Queries

### Search/List Emails
- "what are the last 4 emails" → Last 4 from inbox
- "show me unread emails" → All unread
- "check my inbox" → Recent inbox emails
- "find emails" → Default inbox search
- "list all emails" → Up to 50 emails

### Email Tools Status
- "what email tools do you have"
- "can you send emails"
- "email capabilities"

### Not Yet Supported (Future)
- Sending emails (needs more complex parsing)
- Searching by specific sender/subject
- Reading specific email content

## Files Modified/Created

### Modified
1. **[prompts/supervisor.txt](app/agents/prompts/supervisor.txt)**
   - Added AVAILABLE TOOLS section
   - Added Gmail tool documentation
   - Added usage examples

### Created
1. **[supervisor_with_tools.py](app/agents/supervisor_with_tools.py)**
   - SupervisorWithTools class
   - Pattern detection for email requests
   - Auto-execution of tools
   - Result formatting

2. **[test_supervisor_tools.py](backend/test_supervisor_tools.py)**
   - Test suite for email detection
   - Example usage patterns

## Next Steps

### To Integrate with Chat Agent
Update `scripts/chat_agent.py`:

```python
# Change this line:
from app.agents.supervisor import create_supervisor

# To this:
from app.agents.supervisor_with_tools import create_supervisor_with_tools as create_supervisor
```

Then in the chat loop, use:
```python
response = await agent.chat_with_tools(user_input)
```

### To Add More Patterns
Edit `_detect_email_request()` in [supervisor_with_tools.py](app/agents/supervisor_with_tools.py):

```python
# Add new pattern
elif 'emails from' in message_lower:
    # Extract sender from message
    sender_match = re.search(r'from\s+([^\s]+@[^\s]+)', message_lower)
    if sender_match:
        return {
            'tool': 'search_emails',
            'args': {
                'query': f'from:{sender_match.group(1)}',
                'max_results': 10
            }
        }
```

### To Enable Sending Emails
Add complex parsing for email composition:
```python
elif 'send email to' in message_lower:
    # Extract to, subject, body from natural language
    # This requires more sophisticated NLP
    ...
```

## Advantages of This Approach

✅ **Works with any LLM**: No function calling support needed
✅ **Fast**: Pattern matching is instant
✅ **Predictable**: Clear rules for when tools execute
✅ **Extensible**: Easy to add new patterns
✅ **Debuggable**: Can see exactly what pattern matched

## Limitations

⚠️ **Pattern-Based**: May miss complex queries
⚠️ **Email Sending**: Needs manual implementation for complex parsing
⚠️ **Query Syntax**: Users must phrase requests in expected patterns

## Alternative: Function Calling (Future)

For better natural language understanding, consider:
1. Switch to OpenAI GPT-4 or Claude (native function calling)
2. Use LangChain with function calling agents
3. Fine-tune Ollama model for tool use

But the current pattern-based approach works well for common queries!

## Summary

The Supervisor now has Gmail tools that work through:
1. **System Prompt**: Tells LLM about available tools
2. **Pattern Detection**: Recognizes email requests
3. **Auto-Execution**: Runs tools and formats results
4. **Fallback**: Regular chat for non-email queries

Try it with: `python test_supervisor_tools.py`
