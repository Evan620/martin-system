# Agent System Prompts

This directory contains the system prompts for all AI agents in the ECOWAS Summit TWG Support System.

## Structure

Each agent has its own `.txt` file containing its complete system prompt:

```
prompts/
├── README.md                        # This file
├── supervisor.txt                   # Supervisor Agent prompt
├── energy.txt                       # Energy & Infrastructure TWG
├── agriculture.txt                  # Agriculture & Food Systems TWG
├── minerals.txt                     # Critical Minerals & Industrialization TWG
├── digital.txt                      # Digital Economy & Transformation TWG
├── protocol.txt                     # Protocol & Logistics TWG
└── resource_mobilization.txt        # Resource Mobilization TWG
```

## Prompt Structure

Each prompt file follows this standard structure:

```
You are the [AGENT NAME] for ECOWAS Summit 2026.

ROLE:
[Description of the agent's primary role]

EXPERTISE:
- [Domain knowledge area 1]
- [Domain knowledge area 2]
...

RESPONSIBILITIES:
1. [Key responsibility 1]
2. [Key responsibility 2]
...

CONTEXT:
[Background information about the domain/pillar]

KEY PRIORITIES:
- [Priority 1]
- [Priority 2]
...

OUTPUT STYLE:
- [Style guideline 1]
- [Style guideline 2]
...
```

## Usage

### Loading Prompts in Code

```python
from app.agents.prompts import get_prompt

# Load a specific agent prompt
energy_prompt = get_prompt("energy")

# List all available agents
from app.agents.prompts import list_agents
agents = list_agents()

# Get all prompts at once
from app.agents.prompts import get_all_prompts
all_prompts = get_all_prompts()
```

### Modifying Prompts

1. Edit the relevant `.txt` file in this directory
2. The changes will be automatically loaded next time an agent is initialized
3. For immediate reload during development:

```python
from app.agents.prompts import reload_prompts
reload_prompts()  # Clears cache
```

## Agent Descriptions

### Supervisor
- **Role**: Central coordinator for all TWGs
- **Focus**: Strategic coordination, policy synthesis, cross-TWG alignment
- **File**: [supervisor.txt](supervisor.txt)

### Energy & Infrastructure TWG
- **Role**: Energy transition and power integration expert
- **Focus**: WAPP, renewable energy, regional power infrastructure
- **File**: [energy.txt](energy.txt)

### Agriculture & Food Systems TWG
- **Role**: Food security and agribusiness coordinator
- **Focus**: Agricultural value chains, food sovereignty, rural development
- **File**: [agriculture.txt](agriculture.txt)

### Critical Minerals & Industrialization TWG
- **Role**: Mining value chain and industrialization expert
- **Focus**: Mineral processing, beneficiation, extractive industries governance
- **File**: [minerals.txt](minerals.txt)

### Digital Economy & Transformation TWG
- **Role**: Digital infrastructure and innovation coordinator
- **Focus**: Broadband, fintech, e-government, tech ecosystems
- **File**: [digital.txt](digital.txt)

### Protocol & Logistics TWG
- **Role**: Summit operations and diplomatic protocol manager
- **Focus**: Event logistics, scheduling, accreditation, venue coordination
- **File**: [protocol.txt](protocol.txt)

### Resource Mobilization TWG
- **Role**: Investment pipeline and Deal Room manager
- **Focus**: Project finance, investor matchmaking, bankability assessment
- **File**: [resource_mobilization.txt](resource_mobilization.txt)

## Best Practices

### When Editing Prompts

1. **Be Specific**: Clear, actionable instructions work better than vague guidance
2. **Maintain Structure**: Keep the standard sections (ROLE, EXPERTISE, etc.)
3. **Stay Focused**: Each agent should have a clear, distinct domain
4. **Test Changes**: After editing, test with relevant queries
5. **Version Control**: Commit prompt changes with clear descriptions

### Prompt Engineering Tips

1. **Context First**: Provide background before instructions
2. **Use Examples**: When possible, show what good output looks like
3. **Define Boundaries**: Be explicit about what the agent should/shouldn't do
4. **Output Format**: Specify desired format, tone, and level of detail
5. **Consistency**: Use similar terminology across all agent prompts

## Testing Prompts

After modifying a prompt, test it:

```bash
# Start the chat interface
cd backend
python3 scripts/chat_agent.py --agent energy

# Or test via Python
python3 -c "
from app.agents.energy_agent import create_energy_agent
agent = create_energy_agent()
response = agent.chat('What are ECOWAS renewable energy targets?')
print(response)
"
```

## Troubleshooting

### Prompt Not Loading

1. Check file exists: `ls -la prompts/`
2. Verify filename matches agent_id (e.g., `energy.txt` for agent_id `energy`)
3. Check file permissions: `chmod 644 prompts/*.txt`

### Changes Not Appearing

1. Clear the cache: `reload_prompts()` in code
2. Restart the application/agent
3. Verify file was saved correctly

### Agent Behaving Unexpectedly

1. Review the prompt structure and content
2. Check for conflicting instructions
3. Test with simple, clear queries first
4. Compare with working agent prompts

## Contributing

When adding a new agent:

1. Create `[agent_id].txt` in this directory
2. Add `agent_id` to `AVAILABLE_AGENTS` in `prompts.py`
3. Follow the standard prompt structure
4. Add entry to this README
5. Create tests for the new agent

---

**Last Updated**: 2025-12-26
**Maintained By**: ECOWAS Summit Development Team
