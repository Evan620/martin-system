---
name: waiis-design
description: >-
  Apply the WAIIS "Quiet Paper" design system when building or reskinning any
  frontend UI in this repo (frontend/src/**). Use whenever a page, component,
  card, layout, modal, table, or form is created or restyled, or when the user
  mentions Quiet Paper, the calm/warm-paper look, the design system, tokens,
  spacing, motion, or "make it smoother / calmer / more consistent." This is the
  app's design law — invoke it before writing JSX/CSS so the look stays coherent.
---

# WAIIS — Quiet Paper Design System

Quiet Paper is the calm evolution of WAIIS's existing *Quiet Executive* system,
inspired by the `projectng` / Claude warm-paper aesthetic. Three moves define it:

1. **Warm paper, not cool grey** — backgrounds are warm off-white; text is warm near-black.
2. **Flat, not glass** — surfaces are `1px border + rounded-2xl + no shadow`. Retire
   `backdrop-blur` glass cards.
3. **It moves** — every page assembles itself with a staggered **blur-slide** entrance, and
   every clickable element dips on press (`clickable-scale`).

The accent is **teal**. Use it sparingly: primary actions, active nav, "new" dots, success.

## When to use this skill
- Building or restyling any view under `frontend/src/`.
- Adding a card, KPI strip, table, modal, button, input, dropdown, badge, sidebar item.
- Any request like "make it calmer / smoother / match the design / more consistent."

## Reference files (read the ones you need)
- **`architecture.md`** — ⭐ the **typography + table/list architecture** faithful to the template.
  Read this BEFORE building any heading, label, table, list, or card — it's what makes the design
  *the template's*, not a recolor of ours.
- **`tokens.css`** — the color + type tokens (warm paper, teal accent). Drop-in for the
  `:root` / `.dark` blocks in `frontend/src/index.css`.
- **`motion.css`** — `blur-slide` entrance, stagger utilities, `clickable-scale`, theme
  transition, reduced-motion guard. Append to `index.css`.
- **`components.md`** — copy-paste React + Tailwind/inline-style recipes for every surface,
  written in this repo's conventions (CSS-var tokens via `var(--…)`, Material Symbols icons).

## Non-negotiable rules (the "law")

### Color & surfaces
- Use the **token variables** (`var(--bg)`, `var(--surface)`, `var(--ink-700)`, `var(--accent)`)
  — never hard-code hex in components. The tokens carry light/dark for free.
- **Cards are flat:** `background: var(--surface)`, `border: 1px solid var(--border)`,
  `border-radius: 16px`, **no box-shadow** (or at most a hairline `0 1px 2px rgba(0,0,0,.03)`).
- **Do NOT use `backdrop-filter` / glass** for cards. (Allowed only on the sticky topbar.)
- Accent (teal) is for **signal**, not decoration: primary buttons, active nav, badges,
  "new" dots, focus rings, success. Most of the UI is paper + ink.

### Typography — follow the **font architecture** in `architecture.md` (do NOT reuse the old type scale)
- **Headings = Geist `font-display` (weight 800, `tracking-tight`). NO serif.** Retire
  `Source Serif 4` as the heading default — the template has none; serif headings are "the old look."
- **Numerals & machine data = Geist Mono** (`.font-mono-geist`): KPI numbers, table figures,
  money, dates, times, counts, codes. This mono-for-data move is signature.
- **Eyebrow / column labels** (`.qp-eyebrow`): `text-[10px] uppercase tracking-wider`, ink-400/500.
- **Status pills**: `text-[8px] font-bold uppercase tracking-wider` with a `/10`–`/12` bg tint.
- Base UI text is **12px** (`text-xs`), quiet and small. Full ramp + examples → `architecture.md §1`.

### Tables & lists — follow the **table architecture** in `architecture.md` (do NOT reuse our dense `resp-table`)
- The template uses **airy flat-card lists / grids / kanban**, not dense bordered `<table>`s.
- Rows are **flat cards** (`qp-card`, `p-4`, gap-3), with dot+title+count-pill headers, status pills,
  meta in mono, and optional Grid/List view toggles. Real columns → CSS-grid table (not `<table>`)
  with `.qp-eyebrow` headers, generous `px-4 py-3.5`, hairline row borders, `hover:bg-surface-2`,
  mono numerals. Full recipes → `architecture.md §2`.

### Motion (this is the "smooth")
- **Every page/route container** gets `class="animate-blur-slide"`.
- **Lists/grids of cards** stagger their children: either the `.stagger-1…8` classes or an
  inline `style={{ animationDelay: \`${i * 60}ms\` }}` per item (60ms step).
- **Every clickable** (button, nav item, icon button, card-as-link) gets `clickable-scale`.
- **Theme toggle / color changes**: `transition: background-color .3s, color .3s, border-color .3s`.
- Always honor `prefers-reduced-motion` (the guard is in `motion.css`).

### Radii & spacing
- Cards/modals: `16px` (rounded-2xl). Inputs/buttons/dropdowns/badges: `10–12px`.
  Pills/FAB: `999px`. Avoid sharp 4px corners on content surfaces.
- Generous breathing room: card padding `20px` (`p-5`), section gaps `24px` (`gap-6`).

### Icons
- Keep **Material Symbols Outlined** (already used in `ModernLayout`). Icon color
  `var(--ink-500)`; active/teal where it signals state. `font-size: 18–20px`.

## Reskin checklist (per page)
1. Wrap the page's root element in `animate-blur-slide`.
2. Replace `glass-card` / `.card` / `backdrop-blur` surfaces with the **flat card** recipe.
3. Swap any hard-coded greys/blues for **tokens** (`var(--…)`); ensure teal accent.
4. Add `clickable-scale` to buttons / nav items / clickable rows.
5. Convert section/field headers to **eyebrow labels**.
6. Stagger any card grid (`animationDelay: i*60ms`).
7. Verify dark mode still reads (tokens handle it, but eyeball contrast).
8. Gate: `npx tsc --noEmit` + `npm run build` + `npm run lint` must pass.

## Anti-patterns (do not do)
- ❌ Frosted-glass cards (`backdrop-filter: blur(...)`) for content.
- ❌ Heavy drop shadows / glows. Quiet Paper is flat.
- ❌ Cool slate-grey backgrounds. Use the warm `--bg`.
- ❌ Teal everywhere. It's a signal color, used sparingly.
- ❌ Snapping theme changes with no transition.
- ❌ Static pages with no entrance motion.
- ❌ Hard-coded hex in components instead of tokens.
