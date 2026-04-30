# Icon System

Two icon kinds:

- **Iconify** — massive online / offline icon sets (mdi / material-symbols / carbon / ...)
- **Local SVG** — project-specific logo / business glyphs

Both render through `<svg-icon>`; menus / routes use the same field (`icon` + `iconType`).

## Modes

| Mode | Network | Range |
|---|---|---|
| Online Iconify | required | 100,000+ icons |
| Offline Iconify | none | installed sets |
| Local SVG | none | your `src/assets/svg-icon/` |

### Online Iconify

Nothing to install — browse [icones.js.org](https://icones.js.org/), pick `mdi:home` etc., and use directly. Iconify lazy-loads from a CDN.

### Offline Iconify

```bash
cd web && pnpm add @iconify/json   # download all sets (~90MB, one-time)
```

Vite then inlines the icons you actually use into the bundle — no network at runtime. Strongly recommended for production.

### Local SVG

Drop `.svg` files into [web/src/assets/svg-icon/](../../../web/src/assets/svg-icon/); they're auto-registered with names matching the filename. `logo.svg` → `<svg-icon local-icon="logo" />`.

## Prefix config

```dotenv
# web/.env
VITE_ICON_PREFIX=icon
VITE_ICON_LOCAL_PREFIX=icon-local
```

Direct component form (auto-registered by unplugin-icons):

- Iconify: `<icon-mdi-home />`, `<icon-material-symbols-settings-rounded />`
- Local: `<icon-local-logo />`

For dynamic icons use `<svg-icon>`. See [Usage](/en/frontend/icon/usage).

## In menus

Backend `Menu.icon` + `Menu.icon_type`:

```python
{"icon": "mdi:account-group", "icon_type": "1"}        # Iconify
{"icon": "logo",              "icon_type": "2"}        # local SVG
```

`icon_type` enum: `"1"=iconify`, `"2"=local`. Frontend renders by prefix.

## Recommended icon sets

| Use | Recommended |
|---|---|
| General UI | `mdi:` (Material Design Icons) |
| Modern, flat | `material-symbols:` |
| Carbon / IBM style | `carbon:` |
| Clean lines | `tabler:` |
| Chinese / domain-specific | `icon-park-outline:` |

Powered by [unplugin-icons](https://github.com/unplugin/unplugin-icons) + [@iconify](https://iconify.design/).

## See also

- [Usage](/en/frontend/icon/usage)
