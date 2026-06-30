# Quiet Paper — Component Recipes (WAIIS)

Copy-paste recipes in this repo's conventions: CSS-var tokens via `var(--…)`, inline
`style` for shell/structure (matches `ModernLayout.tsx`), Tailwind utilities where the
codebase already uses them, Material Symbols icons. **Never hard-code hex — use tokens.**

> Rule of thumb: surfaces are flat (`border` + `rounded-2xl` + no shadow), accent is teal
> and used sparingly, everything clickable gets `clickable-scale`, page roots get
> `animate-blur-slide`.

---

## Flat card (the core surface — replaces `glass-card`/`.card`)
```tsx
<div
  className="qp-transition"
  style={{
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-card)',   /* 16px */
    padding: 20,
  }}
>
  {/* … */}
</div>
```
As a Tailwind component class (put in `@layer components` of index.css):
```css
.qp-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}
```
**Do not** add `backdrop-filter`/`blur`. A hairline shadow is the *most* you may add:
`box-shadow: 0 1px 2px rgba(0,0,0,.03);`

## Page wrapper (entrance motion)
```tsx
export default function SomePage() {
  return (
    <div className="animate-blur-slide" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* page content */}
    </div>
  );
}
```

## Card grid with stagger
```tsx
<section style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24 }}>
  {metrics.map((m, i) => (
    <div
      key={m.label}
      className="qp-card animate-blur-slide"
      style={{ padding: 20, animationDelay: `${i * 60}ms` }}
    >
      <div className="qp-eyebrow">{m.label}</div>
      <p style={{ fontWeight: 800, fontSize: 26, letterSpacing: '-0.01em', color: 'var(--ink-900)', marginTop: 8 }}>
        {m.value}
      </p>
    </div>
  ))}
</section>
```

## Eyebrow label (section / field headers)
```tsx
<div className="qp-eyebrow">Main Menu</div>
/* or inline: */
<span style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase',
               fontWeight: 600, color: 'var(--ink-500)' }}>Investors</span>
```

## Primary button (teal)
```tsx
<button
  className="clickable-scale qp-transition"
  style={{
    background: 'var(--accent)', color: 'var(--accent-ink)',
    border: 'none', padding: '9px 16px', borderRadius: 'var(--radius-ctl)',
    fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
  }}
>
  Save
</button>
```

## Secondary / ghost button
```tsx
<button
  className="clickable-scale qp-transition"
  style={{
    background: 'var(--surface)', color: 'var(--ink-700)',
    border: '1px solid var(--border)', padding: '9px 16px',
    borderRadius: 'var(--radius-ctl)', fontSize: 13, fontWeight: 500,
    cursor: 'pointer', fontFamily: 'inherit',
  }}
>
  Cancel
</button>
```

## Icon button (topbar style)
```tsx
<button
  className="clickable-scale qp-transition"
  style={{
    width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 'var(--radius-ctl)', color: 'var(--ink-600)', cursor: 'pointer',
  }}
>
  <span className="material-symbols-outlined" style={{ fontSize: 20 }}>notifications</span>
</button>
```

## Sidebar nav item (active = teal)
```tsx
<button
  onClick={() => navigate(item.path)}
  className="clickable-scale qp-transition"
  style={{
    position: 'relative', display: 'flex', alignItems: 'center', gap: 10,
    width: '100%', textAlign: 'left', padding: '8px 10px 8px 14px',
    fontSize: 13, fontWeight: on ? 600 : 400,
    color: on ? 'var(--ink-900)' : 'var(--ink-600)',
    background: on ? 'var(--accent-soft)' : 'transparent',
    border: 'none', borderRadius: 10, cursor: 'pointer', fontFamily: 'inherit',
  }}
>
  {on && <span style={{ position: 'absolute', left: 0, top: 8, bottom: 8, width: 2,
                        background: 'var(--accent)', borderRadius: 1 }} />}
  <span className="material-symbols-outlined"
        style={{ fontSize: 18, color: on ? 'var(--accent)' : 'var(--ink-500)' }}>
    {item.icon}
  </span>
  <span>{item.label}</span>
</button>
```

## Badge / pill (teal-tinted signal)
```tsx
<span style={{
  fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 999,
  background: 'var(--accent-soft)', color: 'var(--accent)',
}}>3 New</span>
```

## Input field
```tsx
<input
  className="qp-transition"
  style={{
    width: '100%', padding: '9px 12px', fontSize: 13, fontFamily: 'inherit',
    background: 'var(--surface)', color: 'var(--ink-900)',
    border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', outline: 'none',
  }}
  onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent)';
                    e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-soft)'; }}
  onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)';
                   e.currentTarget.style.boxShadow = 'none'; }}
/>
```

## Dropdown trigger (chevron rotates when open)
```tsx
<button className="clickable-scale qp-transition" style={{ /* …like ghost button… */ }}>
  <span>{selected || 'Select option'}</span>
  <span className="material-symbols-outlined qp-transition"
        style={{ fontSize: 18, color: 'var(--ink-400)',
                 transform: open ? 'rotate(180deg)' : 'none' }}>
    expand_more
  </span>
</button>
```

## Skeleton loader (paper-tinted, pulses)
```tsx
<div className="qp-card" style={{ padding: 20 }}>
  <div className="animate-pulse" style={{ height: 12, width: '40%', borderRadius: 6,
        background: 'var(--ink-200)' }} />
  <div className="animate-pulse" style={{ height: 24, width: '60%', borderRadius: 6,
        background: 'var(--ink-200)', marginTop: 12 }} />
</div>
```

## Table → keep WAIIS's responsive `resp-table-mobile` pattern
Reuse the existing responsive table CSS in `index.css`. Just restyle: header row uses
`.qp-eyebrow`, row hover `background: var(--surface-2)`, borders `var(--border)`, and wrap
the table container in `animate-blur-slide`.

## Sticky topbar (the ONE allowed glass surface)
```tsx
<header
  style={{
    height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 32px', borderBottom: '1px solid var(--border)',
    background: 'color-mix(in srgb, var(--surface) 70%, transparent)',
    backdropFilter: 'blur(8px)', position: 'sticky', top: 0, zIndex: 30,
  }}
>
  {/* … */}
</header>
```
