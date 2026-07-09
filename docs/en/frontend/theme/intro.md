# Theme System

Two parts:

- **Component library theme** — Naive UI applies a set of semantic colors + dark mode via `n-config-provider`
- **UnoCSS theme** — the same color scale is injected into UnoCSS so templates can `class="text-primary bg-primary-100"`

One source of truth keeps both downstream layers in sync — no hard-coded colors.

## How it works

```
src/theme/settings.ts (theme defaults)
       │
       ▼
useThemeStore (Pinia)              ── user-selected color / mode
       │
       ├─→ generate Naive UI overrides ── inject into NConfigProvider
       └─→ generate CSS variables + UnoCSS ── written to :root and unocss.config.ts theme.colors
```

Source: [src/theme/](../../../web/src/theme/) and [src/store/modules/theme/](../../../web/src/store/modules/theme/).

## Theme colors

5 **semantic colors**, each with 11 shades (50–950):

| Semantic | Default | Use |
|---|---|---|
| `primary` | blue-green | primary actions / highlight |
| `info` | blue | neutral info |
| `success` | green | success state |
| `warning` | orange | warning |
| `error` | red | errors / destructive actions |

Each color auto-derives `text-{name}` / `bg-{name}` / `border-{name}` UnoCSS utilities.

## Dark mode

- Toggle: top-right "theme mode" button (light / dark / follow system)
- Implementation: add / remove `class="dark"` on `<html>`
- UnoCSS uses the `dark:` prefix: `<div class="bg-white dark:bg-gray-800">`

## Layout modes

| Mode | Use |
|---|---|
| Vertical | standard back-office (default) |
| Horizontal | top nav, no sidebar |
| Vertical-Mix | multi-level sidebar (with secondary panel) |
| Horizontal-Mix | top nav + sidebar |

Toggle: user picks in the settings drawer; `useThemeStore.layout.mode` persists to localStorage.

## i18n & theme

- Theme color: unrelated to i18n
- Mode / layout: unrelated to i18n
- Theme-related labels (e.g. "Theme color" in the drawer) use i18n keys

## Where defaults live

[src/theme/settings.ts](../../../web/src/theme/settings.ts) is the **project-level default** (used on first visit / after clearing local storage). The user's actual choice persists in `localStorage.themeColor` / `themeScheme` / `layout` etc.

## See also

- [Configuration](/en/frontend/theme/config) — all theme fields
- [UnoCSS theme](/en/frontend/theme/unocss) — how to use theme colors in classes
