# 代码规范

每个分类的细节见各专题文档：

- [命名规范](./naming.md) — 文件 / 类 / 函数 / 路径 / 角色 / 按钮 / 路由名
- [Vue 书写风格](./vue.md) — SFC script 顺序、模板规则
- [后端风格](./backend.md) — 强制约定清单（响应、Schema、API、CRUD、权限、模型）

## 工具链速览

| 项 | 工具 | 命令 |
|---|---|---|
| 后端 lint / format | Ruff（行宽 200，双引号，规则 E/F/I） | `make fmt` / `make lint` |
| 后端类型 | basedpyright（standard 模式） | `make typecheck` |
| 后端测试 | pytest | `make test` |
| 前端 lint | ESLint（`@soybeanjs/eslint-config-vue`）+ oxlint | `make web-lint` |
| 前端类型 | vue-tsc | `make web-typecheck` |
| 全栈一键 | — | `make check-all` |
| 提交前钩子 | simple-git-hooks | `cd web && pnpm install` 自动安装 |

## 提交前必跑

```bash
make check-all
```

只动了后端 / 前端时，可分别跑 `make check` / `make web-check`。

## VS Code 推荐配置

- 后端：装 [Charliermarsh.ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) + [DetachHead.basedpyright](https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright)
- 前端：装 [Vue.volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) + [dbaeumer.vscode-eslint](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint)
- 保存时自动 fix：在 `.vscode/settings.json` 加 `"editor.codeActionsOnSave": { "source.fixAll": "explicit" }`
