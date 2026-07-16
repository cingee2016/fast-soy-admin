# 主题配置

主题默认值集中在 [src/theme/settings.ts](../../../web/src/theme/settings.ts)，运行时持久化到 localStorage。

## 主要字段

```typescript
export const themeSettings: App.Theme.ThemeSetting = {
  themeScheme: 'light',                  // 'light' | 'dark' | 'auto'
  grayscale: false,                       // 灰度滤镜
  colourWeakness: false,                  // 色弱辅助
  recommendColor: false,                  // 主题色推荐
  themeColor: '#646cff',                  // 主色
  otherColor: {                           // 其他语义色
    info: '#2080f0',
    success: '#52c41a',
    warning: '#faad14',
    error: '#f5222d',
  },
  isInfoFollowPrimary: true,              // info 是否跟随 primary
  layout: {
    mode: 'vertical',                     // 'vertical' | 'horizontal' | 'vertical-mix' | 'horizontal-mix'
    scrollMode: 'content',                // 'wrapper' | 'content'
    reverseHorizontalMix: false
  },
  page: {
    animate: true,
    animateMode: 'fade-slide',            // 切页动画
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

完整类型在 [src/typings/app.d.ts](../../../web/src/typings/app.d.ts) 的 `App.Theme.*`。

## 持久化

| 行为 | 存储 |
|---|---|
| 用户在设置抽屉改了任何字段 | 写到 `localStorage.themeSettings` |
| 清掉 localStorage | 下次启动用 `settings.ts` 默认值 |
| 重置主题 | 设置抽屉里有"重置"按钮，清 localStorage |

## 切换 API

业务里程序化切换：

```typescript
import { useThemeStore } from '@/store/modules/theme';

const themeStore = useThemeStore();

// 切暗色
themeStore.setThemeScheme('dark');

// 改主题色
themeStore.updateThemeColor('#ff6900');

// 改布局
themeStore.setLayoutMode('horizontal');

// 重置全部
themeStore.resetStore();
```

## 主题色 → CSS 变量

每次主题变化触发 `setupThemeVarsToHtml()`：根据当前色生成 11 级色阶，写到 `<html>` 的 CSS 变量：

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

UnoCSS 自动用这些变量产出 `text-primary` / `bg-primary-200` 等。详见 [UnoCSS 主题](./unocss.md)。

## 暗黑模式策略

```typescript
// dark 模式生效时：
document.documentElement.classList.add('dark');
```

UnoCSS 配置 `dark: 'class'`，`dark:` 前缀的样式只在该 class 存在时生效。Naive UI 的 `n-config-provider` 也会同步切换内置的 dark theme overrides。

## 灰度 / 色弱

```typescript
themeStore.toggleGrayscale();          // 全屏滤镜 grayscale(100%)
themeStore.toggleColourWeakness();     // 色弱辅助滤镜
```

适用于敬告 / 国丧等场景，对屏幕所有内容一并生效。

## 相关

- [简介](./intro.md)
- [UnoCSS 主题](./unocss.md)
