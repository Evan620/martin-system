# TWG Subgroups — Design Spec

**Date:** 2026-05-20  
**Status:** Approved  
**Origin:** Tech Alignment meeting, May 19 2026 — action item: "Add Subgroups: Implement functionality to create subgroups within the technical working groups."

---

## Summary

Add the ability to create named sub-groups within any TWG workspace. A subgroup has its own member list and documents, but shares the parent TWG's meetings and AI agent. Subgroup members must already be TWG members.

---

## Data Model

### New table: `subgroups`

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR(255) | Required |
| description | TEXT | Nullable |
| twg_id | UUID | FK → `twgs.id`, cascade delete |
| lead_id | UUID | FK → `users.id`, set null on delete |
| status | VARCHAR(50) | Default `"active"` |
| created_at | DATETIME | Default now |

### New join table: `subgroup_members`

| Column | Type | Notes |
|---|---|---|
| subgroup_id | UUID | FK → `subgroups.id`, cascade delete |
| user_id | UUID | FK → `users.id`, cascade delete |
| joined_at | DATETIME | Default now |

Composite PK on `(subgroup_id, user_id)`.

### Modified table: `documents`

Add `subgroup_id UUID` (nullable, FK → `subgroups.id`, set null on delete). Documents with a `subgroup_id` belong to that subgroup; documents without belong to the parent TWG.

---

## API Routes

All routes nested under `/twgs/{twg_id}/subgroups/`.

### Subgroup CRUD

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/twgs/{twg_id}/subgroups/` | Any authenticated | List all subgroups for a TWG |
| POST | `/twgs/{twg_id}/subgroups/` | Admin / Secretariat Lead / TWG Facilitator | Create subgroup |
| GET | `/twgs/{twg_id}/subgroups/{sg_id}` | Any authenticated | Get subgroup detail |
| PATCH | `/twgs/{twg_id}/subgroups/{sg_id}` | Admin / Secretariat Lead / TWG Facilitator | Update name / description / lead |
| DELETE | `/twgs/{twg_id}/subgroups/{sg_id}` | Admin / Secretariat Lead / TWG Facilitator | Delete subgroup |

### Member Management

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/twgs/{twg_id}/subgroups/{sg_id}/members` | Any authenticated | List subgroup members |
| POST | `/twgs/{twg_id}/subgroups/{sg_id}/members` | Admin / Secretariat Lead / TWG Facilitator | Add member (body: `{ user_id }`) |
| DELETE | `/twgs/{twg_id}/subgroups/{sg_id}/members/{user_id}` | Admin / Secretariat Lead / TWG Facilitator | Remove member |

> **Add member flow:** The frontend presents a dropdown/search of existing TWG members not yet in this subgroup. No new users are created — the user must already exist in the parent TWG.

### Documents

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/twgs/{twg_id}/subgroups/{sg_id}/documents` | Any authenticated | List subgroup documents |

Auth reuses the existing `_check_twg_management_access()` helper.

---

## Frontend

### TWG Workspace — new "Subgroups" tab

A fifth tab added between "Members Manager" and "Copilot" in `TwgWorkspace.tsx`. Renders a new `SubgroupsManager` component.

**Subgroups list view:**
- Header with subgroup count and "+ New Subgroup" button (shown to managers only)
- Each subgroup rendered as a card: name, lead name, member count, document count, active badge, "Open →" link

**Subgroup detail view** (replaces list when a subgroup is opened):
- Back link "← Back to Subgroups"
- Subgroup name, lead, parent TWG name, description
- Two inner tabs: **Members** and **Documents**
- Members tab: member list with lead badge highlighted, "+ Add Member" button
- Documents tab: document list scoped to this subgroup

### New components

| Component | Location | Purpose |
|---|---|---|
| `SubgroupsManager` | `frontend/src/components/workspace/SubgroupsManager.tsx` | Tab root — list + detail routing |
| `SubgroupCard` | inline in SubgroupsManager | Single subgroup row card |
| `SubgroupDetail` | `frontend/src/components/workspace/SubgroupDetail.tsx` | Detail view with Members + Documents tabs |
| `SubgroupMemberManager` | inline in SubgroupDetail | Add / remove members (TWG members only) |

### API service additions

Extend `frontend/src/services/api.ts` with a `subgroups` namespace:

```typescript
subgroups: {
  list(twgId),
  create(twgId, { name, description, leadId }),
  get(twgId, sgId),
  update(twgId, sgId, data),
  delete(twgId, sgId),
  listMembers(twgId, sgId),
  addMember(twgId, sgId, userId),
  removeMember(twgId, sgId, userId),
  listDocuments(twgId, sgId),
}
```

---

## Error Handling & Edge Cases

| Scenario | Behaviour |
|---|---|
| Add non-TWG-member to subgroup | `400: "User must be a TWG member before joining a subgroup"` |
| Remove lead without reassigning | `400: "Reassign the subgroup lead before removing this member"` |
| TWG member removed from parent TWG | Automatically removed from all subgroups in that TWG (handled in existing `removeMember` route) |
| Delete subgroup | Subgroup deleted; documents unlinked (`subgroup_id` → null), not deleted |
| Duplicate subgroup membership | `409: "User is already a member of this subgroup"` |
| Subgroup name conflict within a TWG | `409: "A subgroup with this name already exists in this TWG"` |
| Set lead to non-member | `400: "Subgroup lead must be a member of the subgroup"` |

---

## Out of Scope

- Subgroups do not get their own meetings (use parent TWG meetings)
- Subgroups do not get their own AI agent (use parent TWG Copilot)
- No nested subgroups (no subgroup-of-a-subgroup)
- No bulk-add for subgroup members (can add one at a time from the existing TWG member list)
