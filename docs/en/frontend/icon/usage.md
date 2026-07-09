# Icon Usage

Three forms: direct component, `<svg-icon>`, JSX renderer. The first two cover 99%.

## Direct component (simplest)

[unplugin-icons](https://github.com/unplugin/unplugin-icons) auto-registers on demand:

```vue
<template>
  <!-- Iconify -->
  <icon-mdi-home class="text-2xl" />
  <icon-material-symbols-settings-rounded class="text-primary" />

  <!-- Local SVG -->
  <icon-local-logo />
</template>
```

**Pros**: name checked at compile time; tree-shaken; zero runtime cost
**Cons**: name is template-literal — dynamic switching is awkward

## Dynamic via `<svg-icon>`

For data-driven icons:

```vue
<template>
  <svg-icon icon="mdi:home" />
  <svg-icon :icon="dynamicIconName" />

  <!-- Local -->
  <svg-icon local-icon="logo" />

  <!-- Custom size / color -->
  <svg-icon icon="mdi:check" class="text-success text-2xl" />
</template>
```

`<svg-icon>` is a global component: [src/components/custom/svg-icon.vue](../../../web/src/components/custom/svg-icon.vue).

## Renderer (JSX / TSX)

For NaiveUI APIs that take a VNode (`MessageProvider`, `MenuOption.icon`, ...):

```typescript
import { useSvgIconRender } from '@sa/hooks';
import SvgIcon from '@/components/custom/svg-icon.vue';

const { SvgIconVNode } = useSvgIconRender(SvgIcon);

const icon = SvgIconVNode({ icon: 'mdi:home' });
const localIcon = SvgIconVNode({ localIcon: 'logo' });

// In NMenu
const menuOption = {
  label: 'Home',
  key: 'home',
  icon: () => SvgIconVNode({ icon: 'mdi:home' }),
};
```

## Route / menu icons

Backend `Menu.icon` + `icon_type`:

```python
# init_data.py
{"icon": "mdi:account-group", "icon_type": "1"}     # Iconify
{"icon": "logo",              "icon_type": "2"}     # local
```

Or frontend route meta:

```typescript
meta: {
  icon: 'mdi:home',           // Iconify
  // or
  localIcon: 'logo'           // local
}
```

Sidebar / tabs auto-render.

## Offline mode

```bash
cd web && pnpm add @iconify/json
```

Vite inlines all Iconify icons referenced in templates / config — no network at runtime. Strongly recommended for production.

## Sizing / color

Icons render as inline SVG — **control them with CSS / Tailwind / UnoCSS**:

```html
<icon-mdi-home class="text-3xl text-primary hover:text-primary-700" />
```

| Want | class |
|---|---|
| Size | `text-base / lg / xl / 2xl / ...` (inherits font-size) |
| Color | `text-primary / text-success / text-gray-500` |
| Rotate | `rotate-90 / -rotate-45` |
| Hover | `hover:text-primary` |

## See also

- [Icon system intro](/en/frontend/icon/intro)
- Route meta: [Create routes](/en/frontend/router/create)
