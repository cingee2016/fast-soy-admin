# UnoCSS Theme

Theme colors are injected as CSS variables and exposed by UnoCSS as utilities. Templates can write `class="text-primary bg-primary-100"` directly.

UnoCSS config: [web/uno.config.ts](../../../web/uno.config.ts).

## Use theme colors

```html
<!-- text / bg / border -->
<span class="text-primary">primary text</span>
<div class="bg-primary-100 border border-primary">light primary bg</div>

<!-- semantic colors -->
<button class="bg-success text-white">Submit</button>
<button class="bg-error text-white">Delete</button>
<NTag class="text-warning">Warning</NTag>
```

## 11 shades

| Shade | Use |
|---|---|
| `50` / `100` / `200` | light backgrounds, hover states |
| `300` / `400` | borders, icons |
| `500` | default (same as `primary` without suffix) |
| `600` / `700` | text, emphasis |
| `800` / `900` / `950` | dark-mode bg / dark text |

```html
<div class="bg-primary-50 dark:bg-primary-950">
  <p class="text-primary-700 dark:text-primary-200">...</p>
</div>
```

## Dark mode

```html
<div class="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100">
  light/dark auto switch
</div>
```

Strategy `dark: 'class'`: relies on `<html class="dark">`, toggled by [`useThemeStore`](/en/frontend/theme/config).

## Custom utilities

To add project-level utilities (e.g. `text-balance`), edit `uno.config.ts`'s `shortcuts` / `rules`:

```typescript
shortcuts: [
  ['flex-center', 'flex items-center justify-center'],
  ['card', 'bg-white dark:bg-gray-800 rounded-lg shadow p-4'],
],
```

## Other palettes

UnoCSS preset bundles the Tailwind palette (`gray / red / blue / ...`, each 50–950). **In business code prefer semantic colors** (`primary / success / warning / error / info`) so a global re-skin propagates everywhere; use specific palette colors only when unrelated to the theme.

## Performance

UnoCSS is on-demand — only classes used in templates appear in the final CSS. Use utilities freely without worrying about CSS size.

## Debug

In Chrome devtools, inspect computed style — CSS variables are at `:root`. Changing `--primary-color` updates the whole site instantly (verify the utilities really resolve to CSS variables).

## See also

- [Intro](/en/frontend/theme/intro)
- [Configuration](/en/frontend/theme/config)
- [UnoCSS docs](https://unocss.dev/)
