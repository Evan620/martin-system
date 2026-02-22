# No Data Response Improvements

## Summary

Updated all TWG agent prompts to provide clear, actionable responses when tools return no data, replacing generic "I can help" messages with specific guidance.

## Problem

When TWG agents had no meeting/document data in the system, they would return vague responses like:
> "I can provide summaries and information related to my TWG..."

This was confusing because:
- It didn't clearly state that no data exists
- It didn't explain why this might happen
- It didn't provide actionable next steps

## Solution

Added a new "HANDLING NO DATA SITUATIONS" section to all TWG agent prompts with explicit instructions:

### What Agents Now Say When They Have No Data:

```
"I don't have any [TWG Name] meeting records in the system yet.
This could mean: (a) no meetings have been scheduled yet,
(b) meetings exist but haven't been recorded in the system,
or (c) there's a data access issue.

You can:
• Create meetings through the system's scheduling interface
• Ask the Secretariat (Supervisor agent) to check across all TWGs
• Contact your TWG facilitator to ensure existing data is properly recorded"
```

### Key Improvements

1. **Explicit Statement**: Clearly says "I don't have any data"
2. **Explanation**: Lists possible reasons for missing data
3. **Actionable Steps**: Provides 3 clear next steps
4. **No Generic Vague Responses**: Explicitly forbids "I can help" style messages

## Files Modified

| File | TWG | Change |
|------|-----|--------|
| `prompts/digital.txt` | Digital Economy & Transformation | Added no data handling section |
| `prompts/energy.txt` | Energy & Infrastructure | Added no data handling section |
| `prompts/agriculture.txt` | Agriculture & Food Systems | Added no data handling section |
| `prompts/minerals.txt` | Critical Minerals & Industrialization | Added no data handling section |
| `prompts/protocol.txt` | Protocol & Logistics | Added no data handling section |
| `prompts/resource_mobilization.txt` | Resource Mobilization | Added no data handling section |
| `prompts/supervisor.txt` | Secretariat Supervisor | Added TWG data access explanation section |

## Testing

After these changes, when a user asks a TWG agent with no data:

**Before:**
```
User: "Can I get summaries from Digital TWG?"
Agent: "I can provide summaries and information related to my TWG..."
```

**After:**
```
User: "Can I get summaries from Digital TWG?"
Agent: "I don't have any Digital TWG meeting records in the system yet.
This could mean: (a) no meetings have been scheduled yet, (b) meetings exist
but haven't been recorded in the system, or (c) there's a data access issue.

You can:
• Create meetings through the system's scheduling interface
• Ask the Secretariat (Supervisor agent) to check across all TWGs
• Contact your TWG facilitator to ensure existing data is properly recorded"
```

## Related Issues

This addresses the confusion where:
- Supervisor shows meeting data (cross-TWG view)
- Individual TWG agents return empty results (TWG-scoped view)
- Users don't understand why different agents see different data

The Supervisor prompt now also includes guidance on explaining TWG data access differences to users.

## Root Cause Note

The underlying data distribution issue (`seed_meeting_demo.py` only assigning meetings to the first TWG) is still present and should be fixed separately to ensure all TWGs have demo data.
