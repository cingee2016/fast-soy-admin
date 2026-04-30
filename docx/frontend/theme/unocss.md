# UnoCSS 主题

主题色作为 CSS 变量注入，由 UnoCSS 派生工具类。模板里直接写 `class="text-primary bg-primary-100"` 即可。

UnoCSS 配置在 [web/uno.config.ts](../../../web/uno.config.ts)。

## 使用主题色

```html
<!-- 文字 / 背景 / 边框 -->
<span class="text-primary">主题色文字</span>
<div class="bg-primary-100 border border-primary">浅主题色背景</div>

<!-- 语义色 -->
<button class="bg-success text-white">提交</button>
<button class="bg-error text-white">删除</button>
<NTag class="text-warning">警告</NTag>
```

## 11 级色阶

| 级 | 用途示例 |
|---|---|
| `50` / `100` / `200` | 浅色背景、悬浮态 |
| `300` / `400` | 边框、icon |
| `500` | 默认色（同 `primary` 不带后缀） |
| `600` / `700` | 文字、强调 |
| `800` / `900` / `950` | dark 模式背景 / 深色文字 |

```html
<div class="bg-primary-50 dark:bg-primary-950">
  <p class="text-primary-700 dark:text-primary-200">...</p>
</div>
```

## 暗黑模式

```html
<div class="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100">
  light/dark 自动切换
</div>
```

策略 `dark: 'class'`：依赖 `<html class="dark">`，由 [`useThemeStore`](./config.md) 切换。

## 自定义工具类

需要新增项目级工具类（如 `text-balance`），在 `uno.config.ts` 的 `shortcuts` / `rules` 里加：

```typescript
shortcuts: [
  ['flex-center', 'flex items-center justify-center'],
  ['card', 'bg-white dark:bg-gray-800 rounded-lg shadow p-4'],
],
```

## 主题色之外的色板

UnoCSS preset 自带 Tailwind 色板（`gray / red / blue / ...`，每种 50–950）。**业务里优先用语义色**（`primary / success / warning / error / info`），让全局换肤时一并生效；只在需要"和主题色无关"的颜色时用具体色板。

## 性能

UnoCSS 是按需生成——只有模板里用到的 class 才会出现在最终 CSS 中。可放心使用大量工具类，无需担心 CSS 体积。

## 调试

打开 Chrome devtools 看元素的 computed style，CSS 变量都在 `:root` 层。改 `--primary-color` 立刻看到全站颜色变化（用于验证主题工具类是否接到 CSS 变量）。

## 相关

- [简介](./intro.md)
- [配置](./config.md)
- [UnoCSS 文档](https://unocss.dev/)
