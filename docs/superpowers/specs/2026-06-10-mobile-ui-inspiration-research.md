# Mobile App UI Inspiration — Research Notes

**Date:** 2026-06-10 · Context: the Editorial redesign read like an article; we need a **native-app** visual language. Dark navy (Big Stone #141D38) + bright yellow (Bright Sun #FCDB32) kept.

## 1. Where to find inspiration (real production screens, not concept art)

| Source | Best for |
|---|---|
| **Mobbin** (mobbin.com) | THE gold standard: 100k+ real production iOS/Android screens, searchable by pattern (e.g. "bottom sheet", "segmented control", "dashboard"). Free tier is enough to browse. |
| **Banani** (banani.co/references) | Free Mobbin alternative — real screens from Things 3, Reddit, Perplexity, Threads. |
| **Pablooo.club** | Free, 15k+ UI assets, AI search. |
| **UXArchive** (uxarchive.com) | Free, organized by *task flows* (onboarding, search…). |
| **Page Flows / Appshots** | Recorded *video* flows — motion, sequencing, micro-interactions. |
| **Dribbble/Behance** | Polish & mood only — concept shots, often impractical. Use for color/feel, never layout truth. |

## 2. Real apps to study for OUR app type (dark/dense/dashboard/community)

- **Revolut (esp. Ultra/dark)** — dark navy + metallic accent; stat tiles, account cards, dense rows. Closest spiritual match to Sovereign.
- **CRED** — the masterclass in dark + single-accent discipline and card depth.
- **Spotify** — THE dark + one-accent app: hierarchy from surface elevation + type weight, accent only on the action.
- **Monzo / N26** — list rows with leading icons, chips, collapsing headers; friendly fintech density.
- **Slack / Discord** — community/channel lists: avatar-led rows, unread badges, section headers that work.
- **Linear (mobile)** — dense dark productivity lists, perfect status chips, zero fluff.
- **Todoist / Things 3** — task rows, swipe actions, quick-add patterns for our "Me" tab.
- **Google Calendar / Outlook mobile** — meeting list patterns: date rails, time-led rows, join buttons inline.

## 3. App vs Article — the concrete difference

**What made ours read as an article:** 34px serif display headlines · single editorial column · eyebrow labels everywhere · prose-like whitespace · rows without leading visuals · no tiles/grid · one giant hero per screen.

**Native-app signals to adopt:**
- **Widget/stat tiles** (2-col grid): "Next meeting", "2 tasks due", "8 docs" as tappable tiles, not paragraphs.
- **List rows** with leading icon/avatar + title + meta + trailing chevron/action; 56–72px tall; dividers or card-grouped.
- **Compact collapsing header**: small screen title that grows/shrinks on scroll (sans-serif, 17–20px) — not a 34px serif headline block.
- **Segmented controls** (2–5 options) for Upcoming/Past, All/Mine.
- **Bottom sheets** for quick actions (RSVP, reminder add, doc actions) instead of new pages.
- **Chips** for filters; **badges** for counts; **FAB** stays (✦ Martin).
- **Density**: 16px body max, 13–14px secondary, screen shows 6–10 information units, not 3.
- 8px grid, 44px touch targets, pull-to-refresh, skeletons (keep from current work).

## 4. Dark + single bright accent (yellow) hierarchy rules

- Accent ≈ **10% of any screen**: ONE filled-yellow action + tiny signals (badges, live dots, selected state). Everything else neutral.
- Hierarchy from a **3-step surface ladder** (deep bg → card → raised element) + **type weight/size**, not from headlines.
- Numbers/data get the high contrast (white/ivory, big, semibold); labels recede (70% alpha, 12–13px).
- Yellow text only ≥13px semibold (contrast on navy is fine: ~12:1, AA at all sizes — but discipline beats availability).

**Sources:** [Inspo AI — Mobbin alternatives](https://www.inspoai.io/blogs/mobbin-alternatives) · [Watobu — 7 Mobbin alternatives](https://watobu.com/blogs/7-best-mobbin-alternatives-for-ui-ux-design-inspiration) · [Banani references](https://www.banani.co/references) · [NN/G — Bottom sheets](https://www.nngroup.com/articles/bottom-sheet/) · [Mobbin — segmented controls](https://mobbin.com/glossary/segmented-control) · [Mobbin — cards](https://mobbin.com/glossary/card) · [Envato — color trends](https://elements.envato.com/learn/color-scheme-trends-in-mobile-app-design) · [Eleken — fintech UI examples](https://www.eleken.co/blog-posts/trusted-fintech-ui-examples) · [Tubik — dark UI](https://blog.tubikstudio.com/ui-inspiration-14-elegant-interfaces-using-dark-background/) · [Skins Factory — fintech UX](https://www.theskinsfactory.com/uiux-design-blog/fintech-ui-ux-design)
