# Frontend Overview

Built on [SoybeanAdmin](https://github.com/soybeanjs/soybean-admin): Vue3 + Vite7 + TypeScript + Pinia + UnoCSS + Naive UI. `/web/` is a pnpm workspace; business code in `web/src/`, internal subpackages in `web/packages/`.

## Tech stack

| Tech | Version | Purpose |
|---|---|---|
| Vue | 3.5 | UI framework |
| Vite | 7 | Build |
| TypeScript | 5.9 | Types |
| Naive UI | 2.44 | Components |
| Pinia | 3 | State |
| UnoCSS | 66+ | Atomic CSS |
| Alova | — | HTTP client (business requests) |
| vue-router | 4 | Dynamic routing (server-issued) |
| vue-i18n | 11 | i18n |
| Elegant Router | — | Auto-generates routes from `views/` |
| unplugin-icons | — | On-demand icon registration |

## Layout

```
web/
├── src/
│   ├── views/                # Pages (Elegant Router scans this)
│   ├── service/              # HTTP layer (factory + API functions)
│   │   ├── api/              # fetchXxx, one file per backend module
│   │   └── request/          # interceptors / codes / token refresh
│   ├── typings/              # TS types
│   │   ├── api/              # interfaces matching backend schemas
│   │   ├── app.d.ts
│   │   └── router.d.ts
│   ├── store/                # Pinia
│   │   └── modules/{auth,route,tab,theme,...}/
│   ├── router/               # vue-router wrapper
│   │   ├── elegant/          # auto-generation + transform
│   │   ├── guard/            # guard chain (auth / dynamic / permission)
│   │   └── routes/builtin.ts # public routes (login / error pages)
│   ├── hooks/                # composables (useTable / useAuth / ...)
│   ├── components/           # global components
│   ├── layouts/              # layout components
│   ├── theme/                # theme source (settings.ts / types / utils)
│   ├── locales/              # i18n (zh-CN / en-US)
│   └── assets/svg-icon/      # local SVG icons
├── packages/                 # internal subpackages
│   ├── alova/
│   ├── axios/
│   ├── hooks/
│   ├── utils/
│   ├── color/
│   └── uno-preset/
└── vite.config.ts
```

## Dev commands

```bash
cd web
pnpm install      # install deps
pnpm dev          # dev server (:9527)
pnpm build        # production build
pnpm lint         # ESLint + oxlint
pnpm typecheck    # vue-tsc
```

Or use root `make web-dev / web-build / web-lint / web-typecheck` or `make dev` to start backend + frontend together. See [Commands](/en/reference/commands).

## Relationship with the backend

The frontend **does not** define permissions or visible routes — both come from the backend per-role:

| Data | Source |
|---|---|
| Current user's roles / button permissions | `GET /api/v1/auth/user-info` |
| Public routes (login / error pages) | `GET /api/v1/route/constant-routes` |
| Menu tree visible to the current user | `GET /api/v1/route/user-routes` |
| Dictionary options | `GET /api/v1/system-manage/dictionaries/{type}/options` |

See [Dynamic routes](/en/frontend/router/dynamic) and backend [RBAC](/en/develop/rbac).

## Subtopic entrypoints

| Topic | Start |
|---|---|
| Routing | [Intro](/en/frontend/router/intro) → [Structure](/en/frontend/router/structure) → [Dynamic](/en/frontend/router/dynamic) |
| Request | [Intro](/en/frontend/request/intro) → [Usage](/en/frontend/request/usage) → [Connect backend](/en/frontend/request/backend) |
| Theme | [Intro](/en/frontend/theme/intro) → [Config](/en/frontend/theme/config) → [UnoCSS](/en/frontend/theme/unocss) |
| Icons | [Intro](/en/frontend/icon/intro) → [Usage](/en/frontend/icon/usage) |
| Hooks | [useTable](/en/frontend/hooks/use-table) |

## Style & conventions

SFC structure, naming, etc. — see [Vue style](/en/standard/vue) and [Naming](/en/standard/naming).
