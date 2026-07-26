# Martin Capability Registry

The capability registry makes a Pydantic input model and one async handler the source of truth for an agent tool, an optional authenticated HTTP route, and the existing confirmation gate. It is disabled by default through `CAPABILITY_REGISTRY_ENABLED=false`.

## Declaration format

Declarations live under `backend/app/capabilities/` and use `@capability`:

```python
class CreateThingInput(BaseModel):
    name: str
    twg_id: UUID


@capability(
    name="registry_create_thing",
    description="Create a thing for a TWG after confirmation.",
    danger="write",
    input_model=CreateThingInput,
    scopes=["supervisor", "twg_*", "ADMIN", "TWG_FACILITATOR"],
    http=("POST", "/capabilities/things"),
    summary_template='Create thing: "{name}"',
)
async def registry_create_thing(
    payload: CreateThingInput,
    context: CapabilityContext,
):
    return await create_thing(payload, context.user, context.db)
```

The fields mean:

- `name`: unique snake_case tool and pending-action type.
- `description`: text shown to the LLM.
- `danger`: `read`, `write`, or `destructive`.
- `input_model`: the only parameter declaration; tool JSON Schema and HTTP body validation are derived from it.
- `handler`: an async function receiving the validated model and `CapabilityContext(user, db)`.
- `scopes`: agent IDs/patterns plus `UserRole` names. Agent scopes control tool visibility; role scopes are rechecked at invocation and confirmation.
- `http`: `(method, path)`, or `None` for a tool-only capability.
- `tool_exposed`: set false for HTTP-only declarations.
- `summary_template`: formatted with the validated JSON payload for confirmation cards.
- `agent_allowed`: defaults true for reads/writes. Destructive declarations default false and must explicitly set `agent_allowed=True` to become agent-callable.

`read` handlers run immediately. `write` and `destructive` handlers do not run until the user confirms through `/api/v1/agents/execute`; destructive cards additionally carry `irreversible: true`. Pending actions use the existing route-level store, including its ten-minute expiry and user-ownership check.

## Porting an existing endpoint

1. Identify the endpoint's request model and business logic. Reuse its Pydantic model when it already represents the complete input contract.
2. Add a uniquely named declaration. During migration, prefix the name (for example, `registry_...`) so it cannot collide with a live tool.
3. Put agent IDs and allowed `UserRole` values in `scopes`. Keep resource-level checks such as TWG membership in the handler or reused service.
4. Point `http` at a new non-colliding path, or use `None` for tool-only behavior.
5. For writes, put all mutation inside the handler. The registry calls it only after confirmation.
6. Import the declaration from `load_reference_capabilities()` (or the future central declaration loader), enable the flag locally, and test tool, HTTP, confirmation, ownership, and expiry behavior before removing any legacy surface.

## Worked before/after: create action item

Before, action-item creation has three manually synchronized pieces: the `/action-items/` route with `ActionItemCreate`, a separately written `create_action_item` tool schema, and `_execute_create_action_item` dispatch in `agents.py`.

The reference declaration `registry_create_action_item` reuses `ActionItemCreate` as its sole schema and calls the existing route function as its handler. From that declaration the registry emits:

- the `registry_create_action_item` OpenAI tool schema;
- `POST /api/v1/capabilities/action-items` with existing authentication and DB dependencies;
- a frontend-compatible confirmation card whose `action_type` is `registry_create_action_item`;
- confirmed fallback dispatch to the same handler.

The legacy route, tool, dispatcher branch, and helper remain unchanged while the feature flag is evaluated. Porting the live name and deleting legacy declarations is intentionally a later migration.
