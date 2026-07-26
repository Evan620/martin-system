# Martin Capability Registry

The capability registry makes a Pydantic input model and one async handler the source of truth for an agent tool, an optional authenticated HTTP route, and the existing confirmation gate. It is disabled by default through `CAPABILITY_REGISTRY_ENABLED=false`.

## Declaration format

Declarations live under `backend/app/capabilities/declarations/` and use `@capability`:

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

## Central loading and integrity

`load_all_capabilities()` walks `app.capabilities.declarations` in sorted module order. Adding a domain module anywhere under that package is enough for it to be discovered; startup code and central import lists do not change. Loading is idempotent, and it is a no-op while `CAPABILITY_REGISTRY_ENABLED` is false. The old `load_reference_capabilities()` name remains as a compatibility wrapper around the central loader.

Enabled HTTP and tool startup paths call `validate_registry()` after loading. The validator raises `RegistryValidationError` with a structured report for duplicate names, capability or legacy route-path collisions, invalid summary fields, non-Pydantic input models, synchronous handlers, and empty scope lists. A destructive capability explicitly marked `agent_allowed=True` remains valid but is listed in the report's `destructive_agent_exceptions` audit field.

`read` handlers run immediately. `write` and `destructive` handlers do not run until the user confirms through `/api/v1/agents/execute`; destructive cards additionally carry `irreversible: true`. Pending actions use the existing route-level store, including its ten-minute expiry and user-ownership check.

## Porting an existing endpoint

1. Identify the endpoint's request model and business logic. Reuse its Pydantic model when it already represents the complete input contract.
2. Add a uniquely named declaration. During migration, prefix the name (for example, `registry_...`) so it cannot collide with a live tool.
3. Put agent IDs and allowed `UserRole` values in `scopes`. Keep resource-level checks such as TWG membership in the handler or reused service.
4. Point `http` at a new non-colliding path, or use `None` for tool-only behavior.
5. For writes, put all mutation inside the handler. The registry calls it only after confirmation.
6. Add the declaration module under `app.capabilities.declarations`, enable the flag locally, and test tool, HTTP, confirmation, ownership, and expiry behavior before removing any legacy surface. The central loader discovers it automatically.

## Ported capabilities (batch 1)

13 declarations, all namespaced `registry_*` during migration so none can collide with the 47 live
tools. **8 read, 5 write, 0 destructive.** Destructive endpoints are deliberately absent: they stay
out of the agent's reach unless a declaration explicitly opts in.

| capability | danger | domain |
|---|---|---|
| `registry_list_twg_members` | read | reference |
| `registry_create_action_item` | write | reference |
| `registry_ingest_document` | write | documents |
| `registry_create_project` | write | pipeline |
| `registry_list_buyer_matches` | read | pipeline |
| `registry_list_dfi_matches` | read | pipeline |
| `registry_list_dfi_windows` | read | pipeline |
| `registry_get_pipeline_settings` | read | pipeline |
| `registry_get_meeting_agenda` | read | meetings |
| `registry_approve_meeting_minutes` | write | meetings |
| `registry_get_recurring_meeting` | read | meetings |
| `registry_list_notifications` | read | notifications |
| `registry_mark_all_notifications_read` | write | notifications |

Selected by demand: endpoints the frontend actually calls (`ui-wired`), cross-checked so each was a
genuine gap against the live tool list rather than a duplicate.

### Danger classification rule

Classify by **reversibility and blast radius, never by row count**:

- `read` — no persistent side effect.
- `write` — creates or mutates data, or sends anything outward to a human. Fan-out inherent to ONE
  logical object is still `write`: creating a meeting that writes a participant row per member is
  `write`, because it is one object and deleting it undoes the work. Marking the caller's own
  notifications read is `write`.
- `destructive` — irreversible deletion/overwrite, or fan-out across MANY independent objects or
  people (bulk delete, orphan cleanup, spreadsheet import, a packet for every TWG, mass messaging).
  Not agent-callable by default.

An earlier automated pass used "bulk = destructive" and tagged *creating a meeting* destructive,
which would have locked the agent out of a core ability. That is why the rule above is worded around
reversibility instead.

### Shared-logic extraction

A ported capability must not reimplement its endpoint's logic, or the agent and the UI will drift.
Where a route held logic inline, it was extracted into a service both call:
`services/meeting_capability_service.py`, plus additions to `notification_service.py` and
`recurring_meeting_service.py`. Extractions must be behaviour-preserving; verify by comparing route
counts and every `@router` path before and after, and by confirming outbound side effects (email,
webhook, PDF, audit log) moved rather than disappeared.

### Known limitations

1. **Reads are exposed as `POST .../query`, not `GET`.** `emit_http` binds `input_model` as a request
   body, and GET with a body is not viable, so read capabilities with parameters take POST. Harmless
   to the agent (tool schemas are unaffected) but the generated HTTP surface diverges from the UI's
   REST convention. Adding GET + query-parameter binding to `emit_http` is the fix.
2. **Multipart upload cannot be declared.** `POST /documents/upload` takes `UploadFile` bytes, which a
   Pydantic `input_model` cannot express, so `registry_upload_document` was left unported rather than
   forced into a JSON shape that would change behaviour. It needs either a reference-by-id upload
   service or multipart support in the emitter.
3. **Testing must never send.** `tests/test_tool_calling_live.py::test_send_email` awaits the real
   sender with no skip marker or env gate, so a plain `pytest tests/` on a networked machine with a
   live key would email real recipients. Always pass
   `--ignore=tests/test_tool_calling_live.py`, never run anything in `backend/scripts/`, and block the
   transmit chokepoints (`EmailService._send_via_resend` / `._send_via_smtp`) in tests. Note that
   `EMAIL_TEST_REDIRECT_TO` only reroutes mail to one inbox: a redirect still sends.

## Worked before/after: create action item

Before, action-item creation has three manually synchronized pieces: the `/action-items/` route with `ActionItemCreate`, a separately written `create_action_item` tool schema, and `_execute_create_action_item` dispatch in `agents.py`.

The reference declaration `registry_create_action_item` in `app.capabilities.declarations.reference` reuses `ActionItemCreate` as its sole schema and calls the existing route function as its handler. From that declaration the registry emits:

- the `registry_create_action_item` OpenAI tool schema;
- `POST /api/v1/capabilities/action-items` with existing authentication and DB dependencies;
- a frontend-compatible confirmation card whose `action_type` is `registry_create_action_item`;
- confirmed fallback dispatch to the same handler.

The legacy route, tool, dispatcher branch, and helper remain unchanged while the feature flag is evaluated. Porting the live name and deleting legacy declarations is intentionally a later migration.
