# 图标使用

三种用法：直接组件、`<svg-icon>` 动态组件、JSX 渲染函数。多数场景用前两种。

## 直接当组件用（最简）

[unplugin-icons](https://github.com/unplugin/unplugin-icons) 自动按需注册：

```vue
<template>
  <!-- Iconify 图标 -->
  <icon-mdi-home class="text-2xl" />
  <icon-material-symbols-settings-rounded class="text-primary" />

  <!-- 本地 SVG -->
  <icon-local-logo />
</template>
```

**优点**：图标名编译期就检查、按需打包、无运行时开销
**缺点**：图标名是字符串拼出来的——动态切换不方便

## 动态用 `<svg-icon>`

需要根据数据切换图标时：

```vue
<template>
  <svg-icon icon="mdi:home" />
  <svg-icon :icon="dynamicIconName" />

  <!-- 本地 -->
  <svg-icon local-icon="logo" />

  <!-- 自定义大小 / 颜色 -->
  <svg-icon icon="mdi:check" class="text-success text-2xl" />
</template>
```

`<svg-icon>` 是全局组件，源码在 [src/components/custom/svg-icon.vue](../../../web/src/components/custom/svg-icon.vue)。

## 渲染函数（JSX / TSX）

NaiveUI 的 `MessageProvider`、`MenuOption.icon` 等需要返回 VNode 的场景：

```typescript
import { useSvgIconRender } from '@sa/hooks';
import SvgIcon from '@/components/custom/svg-icon.vue';

const { SvgIconVNode } = useSvgIconRender(SvgIcon);

// 用法
const icon = SvgIconVNode({ icon: 'mdi:home' });
const localIcon = SvgIconVNode({ localIcon: 'logo' });

// 在 NMenu 配置里
const menuOption = {
  label: 'Home',
  key: 'home',
  icon: () => SvgIconVNode({ icon: 'mdi:home' }),
};
```

## 路由 / 菜单图标

后端 `Menu.icon` 字段 + `icon_type`：

```python
# init_data.py
{"icon": "mdi:account-group", "icon_type": "1"}     # Iconify
{"icon": "logo",              "icon_type": "2"}     # 本地
```

或前端路由 meta：

```typescript
meta: {
  icon: 'mdi:home',           // Iconify
  // 或
  localIcon: 'logo'           // 本地
}
```

侧边栏 / 标签页会自动渲染。

## 离线模式

```bash
cd web && pnpm add @iconify/json
```

Vite 构建时把模板 / 配置中提到的所有 Iconify 图标内联进 bundle，运行时不走网络。生产推荐。

## 调整大小 / 颜色

图标本质是 inline SVG，**用 CSS / Tailwind / UnoCSS 直接控制**：

```html
<icon-mdi-home class="text-3xl text-primary hover:text-primary-700" />
```

| 想要 | class |
|---|---|
| 改大小 | `text-base / lg / xl / 2xl / ...`（继承 font-size） |
| 改颜色 | `text-primary / text-success / text-gray-500` |
| 旋转 | `rotate-90 / -rotate-45` |
| hover 高亮 | `hover:text-primary` |

## 相关

- [图标系统简介](./intro.md)
- 路由 meta：[创建路由](../router/create.md)
