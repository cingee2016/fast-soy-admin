# 系统主题

主题分为两部分：

- **组件库主题** — Naive UI 通过 `n-config-provider` 应用一套语义颜色 + 暗黑模式
- **UnoCSS 主题** — 把同一套色阶注入 UnoCSS 配置，模板里 `class="text-primary bg-primary-100"` 可直接使用

源头一份配置，下游同步生效——前端任何位置都不需要硬编码颜色。

## 工作原理

```
src/theme/settings.ts (主题配置原型)
       │
       ▼
useThemeStore (Pinia)              ── 用户选的主题色 / 模式
       │
       ├─→ 生成 Naive UI overrides ── 注入 NConfigProvider
       └─→ 生成 CSS 变量 + UnoCSS  ── 写到 :root 和 unocss.config.ts 的 theme.colors
```

详细实现见 [src/theme/](../../../web/src/theme/) 与 [src/store/modules/theme/](../../../web/src/store/modules/theme/)。

## 主题色

5 种**语义颜色**，每种 11 级色阶（50–950）：

| 语义 | 默认色 | 用途 |
|---|---|---|
| `primary` | 蓝绿 | 主操作 / 高亮 |
| `info` | 蓝 | 中性提示 |
| `success` | 绿 | 成功状态 |
| `warning` | 橙 | 警告 |
| `error` | 红 | 错误 / 危险操作 |

每种色都自动派生 `text-{name}` / `bg-{name}` / `border-{name}` 的 UnoCSS 工具类。

## 暗黑模式

- 切换：右上角的"主题模式"按钮（手动 light / dark / 跟随系统）
- 实现：在 `<html>` 上加 / 删 `class="dark"`
- UnoCSS 用 `dark:` 前缀写 dark-only 样式：`<div class="bg-white dark:bg-gray-800">`

## 布局模式

| 模式 | 适用 |
|---|---|
| Vertical | 标准后台（默认） |
| Horizontal | 顶部 nav，没有侧栏 |
| Vertical-Mix | 多级侧栏（带二级面板） |
| Horizontal-Mix | 顶部 nav + 侧栏 |

切换：用户在右上角设置抽屉里选；`useThemeStore.layout.mode` 持久化到 localStorage。

## i18n 与主题

- 主题色：与 i18n 无关
- 模式 / 布局：与 i18n 无关
- 主题里出现的文本（如设置抽屉里的"主题色"）走 i18n key

## 默认值在哪改

[src/theme/settings.ts](../../../web/src/theme/settings.ts) 是**项目级默认**（首次访问、清掉本地存储后生效）。用户的实际选择持久化在 `localStorage.themeColor` / `themeScheme` / `layout` 等 key。

## 相关

- [配置](./config.md) — 全部主题字段
- [UnoCSS 主题](./unocss.md) — 把主题色用在 class 上
