# TWG Agent UI Redesign — Design Spec

**Goal:** Redesign the TWG Agent chat page (`TwgAgent.tsx`) to match the clean, professional feel of Claude.ai and ChatGPT — removing visual clutter, fixing structural issues, and aligning with how leading AI interfaces handle conversation layout.

**Approach:** Direction A (Claude-Minimal) + Message Style B (document-style AI responses). Pure white canvas, pill input, prompt chips on the empty state, free-flowing AI text with no bubble.

**Scope:** `frontend/src/pages/workspace/TwgAgent.tsx` + `frontend/src/components/agent/EnhancedMessageBubble.tsx`. No backend changes required.

---

## 1. Message Area

### Current problems
- Background is `#f6f6f8` (light gray) on the message area but white on the header and input — creates a patchy, inconsistent feel.
- AI responses use a white rounded-corner bubble box (`border border-slate-200`, `rounded-2xl`) inside the gray background — a box inside a box.
- Emoji reactions (👍 👎) are always visible below every AI message — no top AI interface does this.

### New behaviour
- Message area background: `#ffffff` — same as header and input. No more gray patch.
- **User messages:** right-aligned, light gray rounded pill (`bg-[#f3f4f6]`, `rounded-[18px_18px_4px_18px]`), max-width 72%.
- **AI responses:** no bubble. Text flows freely on white, left-aligned, full readable width (max `680px`). A small coloured label (`● Martin`, in purple, 11px bold) sits above each response to identify the agent.
- **Message actions (copy, retry, thumbs):** rendered at 11px muted gray (`#d1d5db`), visible always but intentionally low-contrast — they recede. No emoji reaction buttons. On hover the parent message, actions become slightly darker (`#6b7280`). No separate reaction row.

---

## 2. Empty / Welcome State

### Current problems
- Greeting uses `bg-clip-text bg-gradient-to-r from-blue-700 to-purple-600` — flashy gradient on plain text looks amateur.
- Three suggestion "cards" are large (`p-5`, `size-10` icon, two lines of body copy) — feels like a marketing page, not a chat prompt.
- Robot icon in a gradient box is oversized for a welcome screen.

### New behaviour
- **Greeting:** plain `font-bold text-[#111827]` heading at 22px — `"Good morning, {firstName}"`. Sub-line in `text-[#6b7280]` — `"How can {agentName} help you today?"`. No gradient, no icon box above it.
- **Suggestion chips:** a `flex flex-wrap gap-2 justify-center` row of small pill buttons. Each chip: `px-[14px] py-[7px] bg-[#f9fafb] border border-[#e5e7eb] rounded-full text-[12px] text-[#374151]`. On click, sets `inputMessage` and focuses input (same as current behaviour). Six chips: Draft minutes · Summarize session · Check availability · Find documents · Action items · Prepare agenda.
- Remove the gradient icon box entirely. The greeting text and chips are the entire empty state.

---

## 3. Input Area

### Current problems
- Two nested containers: outer `bg-white border-t p-4` div wraps an inner `border-2 rounded-2xl shadow-lg` div — creates visual double-frame.
- Textarea lacks `outline-none` — browser default black focus outline shows alongside the blue border-color change.

### New behaviour
- **Single container:** remove the outer padding wrapper. The pill input sits directly on the white background with only `border-t border-[#f1f5f9]` as the section separator.
- **Pill shape:** `border border-[#e5e7eb] rounded-[26px] px-4 py-2.5` — no shadow. On `focus-within`: `border-[#7c3aed]` (purple, matching agent label colour).
- **Textarea:** `outline-none` already applied. Keep `border-none focus:ring-0 bg-transparent resize-none`.
- **Hint line:** below the pill, `text-[10px] text-[#d1d5db] text-center` — `"↵ to send · / for commands · @ to mention an agent"`. Replaces nothing (was absent before) — gives discoverability.
- **Button layout:** attachment icon (left of send) + send button (right, `bg-[#7c3aed] rounded-full`). Remove the separator bar between icons. Voice/mic button removed — it does nothing.

---

## 4. Header

### Current problems
- Two redundant "online" indicators: a green dot on the avatar AND a `● Online` text label.
- Trash button and settings gear are always visible in the header — top interfaces hide these behind overflow or hover.
- Settings and delete are low-frequency actions that shouldn't occupy prime header real estate.

### New behaviour
- **Left:** avatar (keep gradient-coloured circle with initial) + name + single status line `"Online · {TWG name}"`. Remove the second dot from the status text — the avatar dot is sufficient.
- **Right:** two buttons only — context panel toggle (`view_sidebar`) + overflow menu (`more_horiz`). Settings and clear-conversation move into the overflow menu. Stop-generation button still appears inline when `isLoading || isStreaming` (replaces overflow during generation).
- Header height stays the same (`py-3`), keeping vertical rhythm.

---

## 5. What Is Removed

| Element | Reason |
|---|---|
| Gradient text on greeting | Looks cheap; no professional AI interface uses it |
| Gray background on message area | Creates patchy mismatch with header/input |
| AI response bubble box | Cuts off long responses; free-flowing text is the standard |
| Emoji reaction row (always visible) | Consumer-app feel; actions should recede |
| Double input container (outer wrapper + inner card) | Visual double-border; single pill is cleaner |
| Voice/mic button | Nonfunctional — removes clutter |
| Separator bar between input icons | Unnecessary decoration |
| Second green online dot in status text | Redundant with avatar dot |
| Always-visible trash + settings in header | Low-frequency actions → overflow menu |
| `size-16` gradient icon box above greeting | Oversized; greeting text alone is sufficient |

---

## 6. What Is Kept

- Agent avatar (coloured circle with initial + green presence dot) — identity at a glance
- TWG switcher dropdown (for users with multiple TWGs)
- Context panel toggle
- Stop-generation button during streaming
- All existing autocomplete (slash commands, @ mentions)
- `EnhancedMessageBubble` component — refactored internally to drop the bubble box from AI side; user-message bubble rendering stays
- Dark mode support — all new colour tokens need dark equivalents

---

## 7. Files to Change

| File | Change |
|---|---|
| `frontend/src/pages/workspace/TwgAgent.tsx` | Header simplification, empty state redesign, input area restructure, message area bg |
| `frontend/src/components/agent/EnhancedMessageBubble.tsx` | AI response: remove bubble, add agent label, restyle message actions |

No new files. No backend changes.

---

## 8. Acceptance Criteria

1. Message area background is `#ffffff` — no gray patch.
2. AI responses have no bubble box. Text flows left-aligned at max-width `680px`.
3. User messages are right-aligned gray pills.
4. Empty state shows greeting + chip row only — no gradient text, no icon box.
5. Input is a single pill container — no double border, no shadow card.
6. Header right side shows only context-panel toggle and overflow menu (settings + clear inside overflow).
7. No emoji reaction row visible on AI messages.
8. Focus on input shows single purple border only (no black browser outline).
9. Dark mode renders correctly.
