# SignalRoom UI/UX Redesign — Implementation Plan

## Design Decisions

### Color palette: Keep amber, restrain it
After reading the full CSS, amber (`#f0b36a` / `#e9a85d`) is baked into the brand identity — it appears in the brand mark, nav active state, stats, progress bars, meeting status dots, priority badges, and the `title-mark` class. Replacing it with indigo mid-redesign would require touching every single class. **Decision: keep amber as accent, rename it to a calmer `#e8a045` (slightly more muted), and keep the name `--primary`.** In light mode use `#c47a28`. This achieves restraint without a hue change that could break component identity.

### Typography: Keep DM Sans, add Inter as body alternative
DM Sans is referenced throughout but never actually loaded (no `next/font` in layout.tsx and no Google Fonts `<link>` in the HTML head). The CSS `@theme inline` block declares `--font-sans: 'DM Sans', sans-serif` which falls back to system sans silently. **Decision: load both DM Sans and DM Serif Display via `next/font/google` in layout.tsx using the CSS variable method, keeping `--font-sans` and `--font-serif` mapped to the loaded instances.** No font change needed; just fix the missing load.

### globals.css cleanup
The file currently has two `:root` blocks (lines ~1–24 and the second block starting with `--background: #17151d`) and two `@theme inline` blocks. The second overrides the first on dark theme. **Decision: merge into a single `:root` (dark default) + `[data-theme='light']` override + single `@theme inline`. Preserve all tokens. The second block's values (`--card`, `--popover`, `--secondary`, `--accent`, `--destructive`, `--radius`) are the canonical ones — use them as the merged base.**

### Sidebar nav grouping
Four groups with visual section labels:
- **Workspace** (no label shown, top): Overview, Meetings, Action Items  
- **Tools** (label "Tools"): Analytics  
- **Manage** (label "Manage"): Calendar, Team, Archive  
- **Account** (label "Account"): Settings  

The current `navigation` array flat-maps all 9 views. The `ViewName` type already includes all of them. The grouped sidebar will iterate a static grouped structure — no type changes needed.

### Meeting detail two-column layout
Use CSS Grid: `grid-template-columns: 280px 1fr` at ≥1024px, single column below. The left column is `position: sticky; top: 0; height: 100vh; overflow-y: auto` containing an outline nav (section anchor links) + meeting metadata. The right column is the scrollable content. This is purely CSS + HTML — no new dependencies.

---

## TypeScript Risk Assessment

1. **CSS class names used programmatically**: `getMeetingStatusTone()` returns strings like `meeting-ready`, `meeting-processing` — used as className strings in JSX. These must remain valid class names in globals.css. The redesign retains these classes.
2. **`initialsTone()`** returns `avatar-blue`, `avatar-coral`, etc. — keep avatar color classes.
3. **`projectStatusTone()`** returns `status-risk`, `status-review`, `status-track` — keep status classes.
4. **`isActionDone()`** drives conditional `task-done` class — keep this class.
5. **`priority` className** in ActionItemsView: `className={\`priority ${item.priority.toLowerCase()}\`` — produces `priority high/medium/low`. Keep these.
6. The `SettingsView` uses inline `style` props rather than classes — safe to change classes around it.
7. `CalendarView`, `TeamView`, `ArchiveView`, `AnalyticsView` use `muted-text` class which is NOT defined in globals.css currently. This causes no TS error (it's a className string) but it won't style. Add `.muted-text` to globals.css.
8. **No programmatic font class usage** — font is applied via CSS variable on `body`, safe to change font loading.

---

## Final Token Specification

### Dark theme (`:root` default — merged from both existing blocks):
```
--background:         #17151d   (from block 2 — deeper than block 1's #0f1219)
--background-elevated:#1d1a26   (new, between the two blocks' elevated values)
--surface:            #211e29   (= --card from block 2)
--surface-elevated:   #282431   (= --popover from block 2)
--surface-hover:      #2e2a3a   (new hover state)
--foreground:         #f2eee8   (from block 2)
--muted:              #282431   (= --muted from block 2)
--muted-foreground:   #aaa2b1   (from block 2)
--border:             #393342   (from block 2 — more opaque than block 1's rgba)
--primary:            #e8a045   (restrained amber)
--primary-foreground: #17151d
--secondary:          #2a2632   (from block 2)
--secondary-foreground:#f2eee8
--accent:             #e8a045   (= --primary)
--accent-foreground:  #17151d
--destructive:        #d97872   (from block 2)
--success:            #8eb69b
--warning:            #e8a045
--danger:             #d97872
--info:               #89a9ce
--ai:                 #9a8dff
--ring:               #e8a045
--radius:             0.45rem   (from block 2)
--shadow:             rgba(5, 8, 14, 0.55)
--blue:               #89a9ce
--coral:              #d18c85
--green:              #8eb69b
--amber:              #e8a045
--link:               #9ec5ff
--link-hover:         #cfe1ff
--sidebar-width:      220px     (NEW)
--topbar-height:      56px      (NEW)
--content-max-width:  1200px    (NEW)
```

### Light theme (`[data-theme='light']`):
```
--background:         #f4f6fb
--background-elevated:#ffffff
--surface:            #ffffff
--surface-elevated:   #eef3fb
--surface-hover:      #e8eefb
--foreground:         #1c2330
--muted:              #eef3fb
--muted-foreground:   #67758d
--border:             rgba(89, 103, 122, 0.22)
--primary:            #c47a28
--primary-foreground: #ffffff
--secondary:          #eef3fb
--secondary-foreground:#1c2330
--accent:             #c47a28
--accent-foreground:  #ffffff
--destructive:        #d76a5d
--success:            #47a66b
--warning:            #c47a28
--danger:             #d76a5d
--info:               #4f7dd6
--ai:                 #746ae8
--ring:               #c47a28
--radius:             0.45rem
--shadow:             rgba(18, 28, 44, 0.10)
--blue:               #5c8ddb
--coral:              #dc7d68
--green:              #47a66b
--amber:              #c47a28
--link:               #3b6ed8
--link-hover:         #1f4fa8
--sidebar-width:      220px
--topbar-height:      56px
--content-max-width:  1200px
```

---

## Files to Modify

| File | Change summary |
|------|---------------|
| `app/globals.css` | Merge dual `:root` + `@theme inline` blocks; update all design tokens; update sidebar/topbar CSS; add `.muted-text`; add new tokens; update `.sidebar`, `.app-content`, `.topbar`, `.main-content`, `.meeting-detail-layout`; add new meeting detail 2-col CSS; update all component classes per design direction |
| `app/layout.tsx` | Add `next/font/google` imports for DM_Sans + DM_Serif_Display using CSS variable method; apply font variables to `<html>` className |
| `components/signalroom/workspace-shell.tsx` | Redesign `Sidebar` component with grouped nav, 220px width, bottom user section; redesign `Topbar` to 56px; update `Overview` to remove live-dot and use inline stats; update `MeetingsView` to grouped list/table layout; update `ActionItemsView` filter tabs + improved rows; update `main-content` max-width |
| `app/login/page.tsx` | Improve auth panel layout — split panel or cleaner centered card; keep all form logic identical |
| `app/register/page.tsx` | Same improvements as login page; keep all form logic identical |
| `app/meetings/[id]/page.tsx` | Redesign to two-column layout at ≥1024px; left sticky outline + metadata; right scrollable sections; improve summary/decisions/actions/transcript styling; better upload panel; demo callout bar |
| `components/signalroom/views/AnalyticsView.tsx` | CSS class cleanups — consistent spacing, use `view-stack` pattern properly |
| `components/signalroom/views/CalendarView.tsx` | CSS class cleanups — consistent spacing |
| `components/signalroom/views/TeamView.tsx` | CSS class cleanups — consistent spacing |
| `components/signalroom/views/ArchiveView.tsx` | CSS class cleanups — consistent spacing |
| `components/signalroom/views/SettingsView.tsx` | CSS class cleanups — form inputs use auth-form style, consistent spacing |
| `components/signalroom/SearchOverlay.tsx` | Improve overlay layout — grouped results with type labels, icon + title + snippet rows |
| `components/signalroom/dialogs/MeetingDialog.tsx` | Use proper `.dialog-backdrop` with `backdrop-filter`, clean close button, consistent padding |
| `components/signalroom/dialogs/ProjectDialog.tsx` | Already uses `.dialog-backdrop`; minimal improvements to form field styling |
| `components/signalroom/theme-toggle.tsx` | Move to sidebar bottom; minor style adjustments (no logic change) |

---

## Implementation Plan

- [ ] 1. **Merge and redesign globals.css** — the design system foundation.
      Merge the two `:root` blocks and two `@theme inline` blocks into one each. Apply the final token values from the spec above. Add `--sidebar-width`, `--topbar-height`, `--content-max-width` tokens. Update `.sidebar` (220px, grouped nav support), `.app-content` (uses `--sidebar-width`), `.topbar` (56px height), `.main-content` (max-width 1200px, consistent padding). Update all component classes: stats grid → inline row, project rows, meeting list/table, action items (filter tabs, overdue border), transcript (generous line-height, speaker accent), meeting detail 2-column layout classes (`.meeting-detail-layout`, `.meeting-outline`, `.meeting-content`), upload panel dashed border, demo callout bar, auth panel improvements. Add `.muted-text`. Remove the dead `.app-frame` radial gradient background. Keep every existing class name that is referenced programmatically (see TypeScript risk list above).
      Files: `app/globals.css`
      Verify: `pnpm exec tsc --noEmit` passes with 0 errors. The build step (`pnpm build`) completes without CSS parse errors.

- [ ] 2. **Add font loading to layout.tsx**.
      Import `DM_Sans` and `DM_Serif_Display` from `next/font/google`. Configure each with `variable` option: `variable: '--font-sans'` and `variable: '--font-serif'`. Use `subsets: ['latin']` and `display: 'swap'`. Apply both `font.variable` values as className on the `<html>` element alongside the existing `suppressHydrationWarning`. Remove the `antialiased` class from `<body>` and add it to `<html>` instead (alongside font variables). The `@theme inline` block in globals.css already maps `--font-sans` and `--font-serif` CSS variables.
      Files: `app/layout.tsx`
      Verify: `pnpm exec tsc --noEmit` passes. Running `pnpm dev` and loading the app in a browser shows DM Sans font loaded in network tab with no Google Fonts external requests.

- [ ] 3. **Redesign workspace-shell.tsx** — sidebar, topbar, and inline views.
      **Sidebar**: Replace the flat `navigation` array loop with a grouped structure. Define `NAV_GROUPS` as a constant array of `{ label: string | null; items: ViewName[] }[]`:
      - `{ label: null, items: ['Overview', 'Meetings', 'Action Items'] }` (Workspace section — no visible label or a subtle "WORKSPACE" label)
      - `{ label: 'Tools', items: ['Analytics'] }`
      - `{ label: 'Manage', items: ['Calendar', 'Team', 'Archive'] }`
      - `{ label: 'Account', items: ['Settings'] }`
      Sidebar bottom section: ThemeToggle + user initials + user name. Sidebar width: use `--sidebar-width` CSS variable. Active state: left border `border-left: 2px solid var(--amber)` with `background: var(--surface)`. Nav items: 36px height, icon + label, `font-size: 13px`. Collapse the `Search` view from sidebar nav (it's triggered via keyboard shortcut/topbar button — remove it from the sidebar group entirely, so there are only 8 nav items total). Update the `navigation` const and `viewSlugs`/`slugViews` maps accordingly.
      **Topbar**: 56px height, breadcrumb left, search trigger + bell + avatar right. Move ThemeToggle to sidebar bottom (remove from topbar).
      **Overview**: Remove `<span className="live-dot" />` and "System nominal" from the `hero-eyebrow`. Keep greeting and date range. Stats: replace `.stats-grid` CSS grid with `.stats-row` (flex row of 4 inline stat items, smaller typography). Two-column layout: projects list left, upcoming meetings + activity right (already done with `.content-grid` — keep it).
      **MeetingsView**: Replace `.meeting-grid` (3-col card grid) with a grouped list. Group meetings by time period using `getDateRangeLabel()` logic — "This week", "Last week", "Older". Each group has a `.meeting-group-label` header. Each row: `date | title | status badge | duration | participants | →`. Clicking a row calls `onSelect(meeting)` (existing behavior preserved). Keep the router-level navigation to `/meetings/${id}` inside `onSelect` via the parent's `setSelectedMeeting` which opens the dialog — behavior unchanged.
      **ActionItemsView**: Add filter tabs (All / Open / In progress / Done / Overdue) using local state. Improve row design: checkbox, task+source, owner chip, due date, priority badge. Overdue items get `border-left: 2px solid var(--coral)`.
      Files: `components/signalroom/workspace-shell.tsx`
      Verify: `pnpm exec tsc --noEmit` passes. Manually navigate to each view in the dev server — sidebar renders with groups, active state shows left accent, Overview has no live dot, Meetings shows grouped list, Action Items shows filter tabs.

- [ ] 4. **Redesign auth pages** (login.tsx and register.tsx).
      Keep all form logic, state, and submit handlers identical. Improve the `auth-shell` and `auth-panel` styling in globals.css (done in step 1). In the TSX files: wrap the form in a two-section layout — brand/headline on top, form below — using the updated CSS classes. Add a subtle product description line. Ensure the auth panel has a proper back-to-home link on the login page (already has links via `auth-links`). No logic changes.
      Files: `app/login/page.tsx`, `app/register/page.tsx`
      Verify: `pnpm exec tsc --noEmit` passes. Login and register pages render correctly.

- [ ] 5. **Redesign meeting detail page** (`/meetings/[id]/page.tsx`).
      This is the most complex step. The existing page renders everything in a single `<main>` with inline styles.
      
      **Layout change**: Wrap content in a `.meeting-detail-layout` div with CSS Grid (`grid-template-columns: 280px 1fr` at ≥1024px). Left col: `.meeting-outline` (sticky). Right col: `.meeting-content` (scrollable).
      
      **Left column** (sticky outline):
      - Meeting title (truncated), status badge
      - Anchor links list: `#summary`, `#decisions`, `#action-items`, `#transcript`, `#upload`, `#agenda`
      - Meeting metadata grid: start time, mode, duration, participants
      - ICS download button
      - Back button (moved here from top)
      
      **Right column** (content):
      - Full-width page header: `<h1>` with meeting title + breadcrumb "Meetings / title"
      - Demo callout bar (`.demo-callout`) with amber background, styled as a proper bar not an inline panel
      - Upload panel: proper dashed border card (`.upload-dropzone` already exists — improve to `.upload-panel-card`)
      - Summary section with `id="summary"`: AI badge (`.ai-badge` — purple/`var(--ai)` color), summary text in larger font, key points as clean `<ul>` with custom bullets
      - Decisions section with `id="decisions"`: numbered `<ol>`, each item has title bold + description muted + category chip (`.category-chip`)
      - Action items section with `id="action-items"`: Fellow-style rows — checkbox (read-only indicator), title, owner chip, due date, priority badge  
      - Transcript section with `id="transcript"`: each segment has speaker label bold in `var(--primary)`, timestamp in `var(--muted-foreground)` monospace, text with `line-height: 1.7`
      - Agenda section with `id="agenda"`: unchanged logic, improved CSS classes
      
      Keep all existing TypeScript types, `apiFetch` calls, `UploadPanel` component, `AgendaSection` component, polling logic, and state management unchanged. Only change JSX structure and CSS classes.
      Files: `app/meetings/[id]/page.tsx`
      Verify: `pnpm exec tsc --noEmit` passes. Navigate to any meeting URL in dev server — two-column layout renders, outline links scroll to sections.

- [ ] 6. **Clean up secondary views**: AnalyticsView, CalendarView, TeamView, ArchiveView, SettingsView.
      All five views currently use `p className="muted-text"` which has no CSS definition. Add `.muted-text { color: var(--muted-foreground); font-size: 0.875rem; }` to globals.css (done in step 1). For each view:
      - Replace inline `style` props with CSS classes where possible (margins, padding, colors)
      - Ensure `view-heading` h1 aligns with the new 40px serif font size (down from 48px)
      - `SettingsView` form inputs: add `auth-form` class or an equivalent `settings-form` class with proper border, radius, focus ring
      - No logic or API call changes
      Files: `components/signalroom/views/AnalyticsView.tsx`, `components/signalroom/views/CalendarView.tsx`, `components/signalroom/views/TeamView.tsx`, `components/signalroom/views/ArchiveView.tsx`, `components/signalroom/views/SettingsView.tsx`
      Verify: `pnpm exec tsc --noEmit` passes. Navigate to each view in dev server — no visual regressions, consistent spacing.

- [ ] 7. **Redesign SearchOverlay and Dialogs**.
      **SearchOverlay**: The existing `.search-layer`, `.search-dialog`, `.search-input-wrap`, `.search-results`, `.search-result` classes are already well-structured. Improvements: add `.search-group-label` CSS for grouping headers (already used in the template as `.search-group` + `.search-group + .search-group` margin). Group results by `content_type` with type label headers. No logic change to the search API call.
      **MeetingDialog**: Existing `.dialog-backdrop` has `backdrop-filter: blur(5px)` — already good. Improve `.dialog h2` from `font-family: var(--font-serif)` to proper size. Ensure `.dialog-close` has a clean ×. No logic changes.
      **ProjectDialog**: Already well-structured. Minor: use `border-radius: var(--radius)` on inputs, ensure focus ring uses `var(--ring)`.
      Files: `components/signalroom/SearchOverlay.tsx`, `components/signalroom/dialogs/MeetingDialog.tsx`, `components/signalroom/dialogs/ProjectDialog.tsx`
      Verify: `pnpm exec tsc --noEmit` passes. Open search with Ctrl+K — overlay renders with grouped results. Open project dialog — modal renders with backdrop blur.

- [ ] 8. **TypeScript check and build verification**.
      Run full TypeScript check and production build. Fix any type errors introduced by structural changes in the TSX files (most likely: removed `Search` from nav groups, updated `navigation` const type-checking against `ViewName`). Ensure `pnpm build` exits with code 0.
      Files: any file with type errors
      Verify: `pnpm exec tsc --noEmit` exits 0. `pnpm build` exits 0 with no errors.

---

## Sidebar Nav Group Structure (exact)

```
┌─────────────────────────────┐
│  ▣  Signalroom              │  ← brand/workspace name (top)
├─────────────────────────────┤
│  [no group label]           │
│    ⊞ Overview               │  ← nav-item (active: left border)
│    📅 Meetings              │
│    ✓  Action Items          │
├─────────────────────────────┤
│  TOOLS                      │  ← nav-label
│    📊 Analytics             │
├─────────────────────────────┤
│  MANAGE                     │  ← nav-label
│    🗓  Calendar              │
│    👥 Team                  │
│    📦 Archive               │
├─────────────────────────────┤
│  ACCOUNT                    │  ← nav-label
│    ⚙  Settings              │
├─────────────────────────────┤
│  [theme toggle]             │  ← sidebar-bottom
│  ● MA  Mara (user name)     │
└─────────────────────────────┘
```

## Meeting Detail Two-Column Layout (CSS)

```css
.meeting-detail-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 0;
  min-height: calc(100vh - var(--topbar-height));
  align-items: start;
}

.meeting-outline {
  position: sticky;
  top: var(--topbar-height);
  height: calc(100vh - var(--topbar-height));
  overflow-y: auto;
  padding: 2rem 1.5rem;
  border-right: 1px solid var(--border);
}

.meeting-content {
  padding: 2rem 2.5rem;
  max-width: 800px;
}

@media (max-width: 1023px) {
  .meeting-detail-layout {
    grid-template-columns: 1fr;
  }
  .meeting-outline {
    position: static;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--border);
  }
}
```

---

## Verification Commands

```bash
pnpm exec tsc --noEmit       # TypeScript check — must exit 0
pnpm build                   # Production build — must exit 0
```
