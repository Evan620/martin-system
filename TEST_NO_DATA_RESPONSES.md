# Test Scenario: No Data Responses

## Purpose
Test that TWG agents now give clear, actionable responses when they have no meeting/document data, instead of generic "I can help" messages.

## Prerequisites
1. Backend server running
2. Frontend running
3. Logged in as a user with TWG access (Admin or TWG member)

## Test Scenarios

### Scenario 1: TWG with No Data (Most Likely)

**Setup:** Identify which TWG has no meetings by checking the database or trying each one.

**Steps:**

1. **Open the chat interface** for a TWG that likely has no data (try Digital TWG first)

2. **Send this message:**
   ```
   Give me a summary of your TWG's recent meetings
   ```

3. **Expected Response (OLD - BAD):**
   ```
   "I can provide summaries and information related to my own Technical Working Group focused on Digital Infrastructure and Regulatory Harmonization..."
   ```
   ❌ Vague, doesn't address the issue

4. **Expected Response (NEW - GOOD):**
   ```
   "I don't have any Digital TWG meeting records in the system yet. This could mean: (a) no meetings have been scheduled yet, (b) meetings exist but haven't been recorded in the system, or (c) there's a data access issue.

   You can:
   • Create meetings through the system's scheduling interface
   • Ask the Secretariat (Supervisor agent) to check across all TWGs
   • Contact your TWG facilitator to ensure existing data is properly recorded"
   ```
   ✅ Clear, explains why, provides next steps

---

### Scenario 2: Ask for Meeting Minutes

**Steps:**

1. **Send to a TWG with no data:**
   ```
   Do we have minutes from our last meeting?
   ```

2. **Expected Response:**
   - Agent should FIRST call `get_meeting_minutes` tool
   - Tool returns: "No meeting minutes found"
   - Agent should give the new clear "no data" response
   - Should NOT say "I can help you find minutes..."

---

### Scenario 3: Ask for Documents

**Steps:**

1. **Send to a TWG with no data:**
   ```
   Show me all our documents and reports
   ```

2. **Expected Response:**
   - Agent should FIRST call `search_documents` tool
   - Tool returns: "No documents found"
   - Agent should give the new clear "no data" response

---

### Scenario 4: Compare Supervisor vs TWG Agent

**This demonstrates the data access difference**

**Steps:**

1. **Ask Supervisor (general chat):**
   ```
   Show me all meetings across all TWGs
   ```
   - Supervisor should show ALL meetings (cross-TWG view)

2. **Ask Digital TWG agent:**
   ```
   Show me Digital TWG meetings
   ```
   - If Digital TWG has no meetings, should give clear "no data" response
   - Should explain that Supervisor can check across all TWGs

---

### Scenario 5: Cross-TWG Question

**Test that TWG agents explain they can't access other TWGs**

**Steps:**

1. **Send to Digital TWG agent:**
   ```
   Can you show me the Energy TWG meeting summaries?
   ```

2. **Expected Response:**
   ```
   "I can only access Digital TWG data. For Energy TWG summaries, please:
   • Contact the Energy TWG agent directly
   • Ask me (or the Supervisor) to check if we can route your question there"
   ```

---

## Quick Test Commands

### Via cURL (if you want to test API directly)

```bash
# Test Digital TWG (likely has no data)
curl -X POST http://localhost:8000/agents/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Give me a summary of your recent meetings",
    "twg_id": "DIGITAL_TWG_UUID",
    "conversation_id": "test-no-data-123"
  }'

# Test Supervisor (should show all meetings)
curl -X POST http://localhost:8000/agents/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Show me all meetings across all TWGs",
    "conversation_id": "test-supervisor-456"
  }'
```

---

## How to Identify Which TWG Has No Data

### Option 1: Check Database
```sql
SELECT twg.name, COUNT(m.id) as meeting_count
FROM twgs twg
LEFT JOIN meetings m ON m.twg_id = twg.id
GROUP BY twg.id, twg.name
ORDER BY meeting_count;
```

### Option 2: Ask Each TWG
Send "How many meetings do we have?" to each TWG agent and see which returns 0.

---

## Success Criteria

✅ **PASS**: Agent gives clear "no data" message with:
- Explicit statement that no data exists
- Explanation of why this might happen
- Actionable next steps (create meeting, ask Supervisor, contact facilitator)

❌ **FAIL**: Agent gives vague message like:
- "I can provide information..."
- "I'm here to help with..."
- Any response that doesn't explicitly say "no data"

---

## Bonus: Check the Actual Prompt

If you want to verify the prompt changes were applied:

```bash
# Check Digital TWG prompt
grep -A 20 "HANDLING NO DATA SITUATIONS" backend/app/agents/prompts/digital.txt

# Check Energy TWG prompt
grep -A 20 "HANDLING NO DATA SITUATIONS" backend/app/agents/prompts/energy.txt
```

You should see the new "no data" handling instructions.
