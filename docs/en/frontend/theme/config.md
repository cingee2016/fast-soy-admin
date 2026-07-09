# Theme Configuration

Theme defaults live in [src/theme/settings.ts](../../../web/src/theme/settings.ts); runtime values persist to localStorage.

## Main fields

```typescript
export const themeSettings: App.Theme.ThemeSetting = {
  themeScheme: 'light',                  // 'light' | 'dark' | 'auto'
  grayscale: false,                       // grayscale filter
  colourWeakness: false,                  // colour-weakness aid
  recommendColor: false,                  // recommended palette
  themeColor: '#646cff',                  // primary
  otherColor: {                           // other semantic colors
    info: '#2080f0',
    success: '#52c41a',
    warning: '#faad14',
    error: '#f5222d',
  },
  isInfoFollowPrimary: true,              // info follows primary
  layout: {
    mode: 'vertical',                     // 'vertical' | 'horizontal' | 'vertical-mix' | 'horizontal-mix'
    scrollMode: 'content',                // 'wrapper' | 'content'
    reverseHorizontalMix: false
  },
  page: {
    animate: true,
    animateMode: 'fade-slide',            // page transition
  },
  header: {
    height: 56,
    breadcrumb: { visible: true, showIcon: true }
  },
  tab: {
    visible: true,
    cache: true,
    height: 44,
    mode: 'chrome'                        // 'chrome' | 'button'
  },
  fixedHeaderAndTab: true,
  sider: {
    inverted: false,
    width: 220,
    collapsedWidth: 64,
    mixWidth: 90,
    mixCollapsedWidth: 64,
    mixChildMenuWidth: 200
  },
  footer: {
    visible: true,
    fixed: false,
    height: 48,
    right: true
  },
  watermark: { visible: false, text: 'SoybeanAdmin' }
};
```

Full type in [src/typings/app.d.ts](../../../web/src/typings/app.d.ts) `App.Theme.*`.

## Persistence

| Action | Storage |
|---|---|
| User edits any field in the settings drawer | written to `localStorage.themeSettings` |
| Cleared localStorage | next start uses `settings.ts` defaults |
| Reset theme | "Reset" button in settings drawer clears localStorage |

## Switch programmatically

```typescript
import { useThemeStore } from '@/store/modules/theme';

const themeStore = useThemeStore();

themeStore.setThemeScheme('dark');
themeStore.updateThemeColor('#ff6900');
themeStore.setLayoutMode('horizontal');
themeStore.resetStore();
```

## Theme color → CSS variables

Each theme change triggers `setupThemeVarsToHtml()`: generates 11 shades from the current color and writes them to `<html>`'s CSS variables:

```css
:root {
  --primary-color: #646cff;
  --primary-50: #f1f0ff;
  --primary-100: #e0deff;
  --primary-200: #c2bdff;
  /* ... 50, 100, 200, ..., 950 */
  --primary-color-hover: #7a82ff;
  --primary-color-pressed: #5258dd;
  --primary-color-suppl: #4a52e0;
}
```

UnoCSS automatically derives `text-primary` / `bg-primary-200` from these. See [UnoCSS theme](/en/frontend/theme/unocss).

## Dark-mode strategy

```typescript
// when dark mode is active:
document.documentElement.classList.add('dark');
```

UnoCSS is configured `dark: 'class'`, so `dark:` prefix only applies when this class is present. Naive UI's `n-config-provider` switches its built-in dark overrides simultaneously.

## Grayscale / colour weakness

```typescript
themeStore.toggleGrayscale();          // full-screen grayscale(100%) filter
themeStore.toggleColourWeakness();     // colour-weakness aid filter
```

For mourning days etc.; affects the entire screen.

## See also

- [Intro](/en/frontend/theme/intro)
- [UnoCSS theme](/en/frontend/theme/unocss)
