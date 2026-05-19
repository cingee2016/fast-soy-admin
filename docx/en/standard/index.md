# Code Standards

Topics:

- [Naming conventions](/en/standard/naming) — files / classes / functions / paths / role / button / route names
- [Vue style](/en/standard/vue) — SFC script order, template rules
- [Backend style](/en/standard/backend) — enforced checklist (response, schema, API, CRUD, permissions, models)

## Toolchain

| Concern | Tool | Command |
|---|---|---|
| Backend lint / format | Ruff (line 200, double-quote, rules E/F/I) | `just fmt backend` / `just lint backend` |
| Backend types | basedpyright (standard mode) | `just typecheck backend` |
| Backend tests | pytest | `just test backend` |
| Frontend lint | ESLint (`@soybeanjs/eslint-config-vue`) + oxlint | `just lint frontend` |
| Frontend types | vue-tsc | `just typecheck frontend` |
| Full stack | — | `just check` |
| Pre-commit hook | simple-git-hooks | auto-installed via `cd web && pnpm install` |

## Pre-commit gate

```bash
just check
```

Or run only the side you touched: `just check backend` / `just check frontend`.

## Recommended VS Code setup

- Backend: install [Charliermarsh.ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) + [DetachHead.basedpyright](https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright)
- Frontend: install [Vue.volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) + [dbaeumer.vscode-eslint](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint)
- Auto-fix on save: `"editor.codeActionsOnSave": { "source.fixAll": "explicit" }`
