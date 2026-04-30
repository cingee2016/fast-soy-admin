# 图标系统

支持两种图标：

- **Iconify** — 海量在线 / 离线图标集（mdi / material-symbols / carbon / 自定义……）
- **本地 SVG** — 项目专属 logo / 业务图

两套统一通过 `<svg-icon>` 组件渲染，菜单 / 路由配置里也用同一个字段（`icon` + `iconType`）。

## 引入方式

| 方式 | 网络 | 图标范围 |
|---|---|---|
| 在线 Iconify | 需要联网 | 10 万+ 全部图标 |
| 离线 Iconify | 完全离线 | 安装的图标集 |
| 本地 SVG | 完全离线 | 自己放在 `src/assets/svg-icon/` |

### Iconify 在线

无需配置——在图标库（[icones.js.org](https://icones.js.org/)）找到 `mdi:home` 之类的 key 直接用。Iconify 按需从 CDN 加载。

### Iconify 离线

```bash
cd web && pnpm add @iconify/json   # 下载所有图标集（一次性 ~ 90MB）
```

Vite 构建时把用到的图标内联进 bundle，运行时不走网络。生产环境推荐。

### 本地 SVG

把 `.svg` 放到 [web/src/assets/svg-icon/](../../../web/src/assets/svg-icon/)，会被自动注册成名字与文件名一致的图标。例如 `logo.svg` 对应 `<svg-icon local-icon="logo" />`。

## 前缀配置

```dotenv
# web/.env
VITE_ICON_PREFIX=icon
VITE_ICON_LOCAL_PREFIX=icon-local
```

直接以 component 形式用图标时（unplugin-icons 自动注册）：

- Iconify：`<icon-mdi-home />`、`<icon-material-symbols-settings-rounded />`
- 本地：`<icon-local-logo />`

需要动态切换图标时用 `<svg-icon>`，详见 [使用方式](./usage.md)。

## 在菜单里用图标

后端 `Menu.icon` + `Menu.icon_type`：

```python
{"icon": "mdi:account-group", "icon_type": "1"}        # Iconify
{"icon": "logo",              "icon_type": "2"}        # 本地 SVG
```

`icon_type` 枚举：`"1"=iconify`、`"2"=local`。前端会按对应 prefix 渲染。

## 推荐图标库

| 用途 | 推荐 |
|---|---|
| 通用 UI | `mdi:` (Material Design Icons) |
| 现代、扁平 | `material-symbols:` |
| Carbon / IBM 风格 | `carbon:` |
| 简洁线条 | `tabler:` |
| 中文 / 业务专用 | `icon-park-outline:` |

整个工具链由 [unplugin-icons](https://github.com/unplugin/unplugin-icons) + [@iconify](https://iconify.design/) 驱动。

## 相关

- [使用方式](./usage.md)
