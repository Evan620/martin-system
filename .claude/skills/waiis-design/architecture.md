# Quiet Paper — Typography & Table/List Architecture (faithful to projectng)

This is the part that makes it *the template's design*, not a recolor of ours. Copy the
**structure and type ramp**, not just the colors. Derived from projectng's real components
(dashboard.ts, calendar.ts, team.ts, projects/list.ts, sidebar.ts, topbar.ts).

---

## 1. Typography Architecture

**Families**
- **Geist** — everything (body, headings, labels).
- **Geist Mono** — *all numerals & machine data*: KPI numbers, table figures, money, dates,
  times, counts, codes, kbd. This mono-for-data move is a signature of the look.
- **NO serif.** Retire `Source Serif 4` as the heading default — the template has none.
  (WAIIS's serif headings are "what we had"; replacing them is the point.)

**`font-display` (headings)** — add this utility and use it for every section/page heading:
```css
.font-display { font-family: 'Geist', system-ui, sans-serif; font-weight: 800; letter-spacing: -0.02em; }
```
Heading sizes stay **small**: page title `text-md`/`text-lg` (15–18px) `font-display`, section
title `text-xs`/`text-sm font-bold tracking-tight`. Big stat numbers `text-2xl font-extrabold tracking-tight` in **Geist Mono**.

**The type ramp (small & quiet — this is key):**
| Role | Spec |
|---|---|
| Page / section heading | `font-display` (Geist 800) `tracking-tight`, 15–18px |
| Sub-section title | `font-bold text-xs tracking-tight` (12px) |
| Body / cell text | `text-xs` (12px), occasionally `text-[13px]` |
| Eyebrow / column label | `text-[10px] uppercase tracking-wider font-semibold text-[var(--ink-500)]` (`.qp-eyebrow`) |
| Meta (dates, sub-labels) | `text-[9px] font-semibold text-[var(--ink-400)]` — in **Geist Mono** if it's a date/number |
| Status pill / tag | `text-[8px] font-bold uppercase tracking-wider`, `/10` bg tint of its color |
| Big stat number | `text-2xl font-extrabold tracking-tight` **Geist Mono** |

**Rules:** keep it small and quiet — base UI is 12px, not 14px. Labels are uppercase micro-type.
Numbers are mono. Headings are heavy Geist, never serif.

---

## 2. Table / List Architecture

The template **avoids dense bordered `<table>`s**. It composes data as **airy flat-card lists,
grids, and kanban columns**. Pick the pattern that fits; never fall back to our old dense grid.

### A. Section header (above any list/table)
```tsx
<section className="flex flex-col sm:flex-row gap-4 items-center justify-between">
  <div>
    <h2 className="font-display text-md" style={{letterSpacing:'-0.02em'}}>Pipeline</h2>
    <p className="text-xs" style={{color:'var(--ink-400)'}}>14 active deals across 6 TWGs.</p>
  </div>
  {/* optional view toggle, see C */}
</section>
```

### B. List header row + flat-card rows (preferred over dense tables)
```tsx
{/* column/group header */}
<div className="flex items-center justify-between pb-2" style={{borderBottom:'1px solid var(--border)'}}>
  <div className="flex items-center gap-2">
    <span className="w-2.5 h-2.5 rounded-full" style={{background:'var(--accent)'}} />
    <h3 className="font-bold text-xs tracking-tight">In Negotiation</h3>
  </div>
  <span className="text-[10px] font-bold px-2 py-0.5 rounded" style={{background:'var(--surface-2)',color:'var(--ink-500)'}}>8</span>
</div>
{/* a row is a flat card, NOT a <tr> */}
<div className="qp-card group clickable-scale" style={{padding:16, display:'flex', flexDirection:'column', gap:12}}>
  <div className="flex items-start justify-between gap-3">
    <h4 className="font-bold text-xs leading-snug">Project title</h4>
    <span className="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
          style={{background:'color-mix(in srgb, var(--accent) 12%, transparent)', color:'var(--accent)'}}>High</span>
  </div>
  <div className="flex items-center justify-between">
    <span className="text-[9px] font-semibold font-mono-geist" style={{color:'var(--ink-400)'}}>Jun 30 – Jul 14</span>
    <span className="text-[9px]" style={{color:'var(--ink-400)'}}>$2.4M</span>
  </div>
</div>
```

### C. View toggle (Grid/List, Month/Week) — pill group
```tsx
<div className="p-1 rounded-xl border flex items-center" style={{borderColor:'var(--border)', background:'var(--surface-2)'}}>
  {['Grid','List'].map(v => (
    <button key={v} onClick={()=>setView(v)} className="px-3 py-1.5 rounded-lg text-xs font-semibold clickable-scale"
      style={view===v ? {background:'var(--surface)', fontWeight:700, boxShadow:'0 1px 2px rgba(0,0,0,.05)'} : {color:'var(--ink-400)'}}>{v}</button>
  ))}
</div>
```

### D. When real columns ARE needed — CSS-grid table (not `<table>`)
- Header row: `.qp-eyebrow` column labels (`text-[10px] uppercase tracking-wider`), `border-b border-[var(--border)]`, `px-4 py-3`.
- Rows: CSS grid, generous `px-4 py-3.5`, hairline `border-b border-[var(--border)]`, `hover:bg-[var(--surface-2)]` (add `qp-transition`), clickable rows get `clickable-scale`.
- **Numerals/dates/money in Geist Mono** (`.font-mono-geist`). Status as `/10`-tint pills.
- Container: `rounded-2xl border border-[var(--border)] overflow-hidden bg-[var(--surface)]`.
- Optional row entrance: `animate-blur-slide` with `style={{animationDelay: i*40+'ms'}}`.

### E. Skeletons
`animate-pulse` bars: `style={{background:'var(--ink-200)'}}` with rounded corners, while loading.

### F. Spacing rhythm
Page `space-y-6` (24px) · grids `gap-6` · card padding `p-4`/`p-5` · column lists `space-y-3/4`.

### G. Calendar (month grid)
`grid grid-cols-7 grid-rows-5 divide-x divide-y` with `divide-[var(--border)]`; weekday header
row (`grid-cols-7 text-center font-bold text-xs text-[var(--ink-400)] border-b py-3`); day cell
`min-h-[90px] p-3 flex flex-col justify-between` with `text-xs font-bold` day number; event chips
`text-[8px] font-bold rounded px-2 py-0.5` tinted by type; controls = prev/next + Month/Week toggle + Add Event.
