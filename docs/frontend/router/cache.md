# 路由缓存

借 Vue `<keep-alive>` 缓存页面状态——切到其他 tab 再切回来时**不重新创建组件实例**，搜索条件、滚动位置、表单输入都保留。

## 启用

后端菜单声明里：

```python
{"route_name": "manage_user", "keep_alive": True, ...}
```

或前端路由 meta：

```typescript
meta: {
  keepAlive: true
}
```

## 必要条件

`<keep-alive>` 通过组件的 `name` 识别要缓存哪个实例——因此**所有期望被缓存的页面必须 `defineOptions({ name: 'XXX' })`**：

```vue
<script setup lang="ts">
defineOptions({ name: 'ManageUser' });   // ✅ 必须
</script>
```

CLI 自动生成的页面已经带上了 `defineOptions`。手写时容易遗漏。

## onMounted 不再触发

被缓存的组件**不会**重新走 `onMounted`。需要每次激活时刷新数据用 `onActivated`：

```typescript
import { onActivated, onMounted } from 'vue';

onMounted(getData);          // 首次加载
onActivated(getData);        // 每次切回来
```

只想首次加载、激活不刷新——只用 `onMounted` 即可。

## 何时缓存被清掉

| 行为 | 是否清缓存 |
|---|---|
| 切到其他 tab | ❌ 保留 |
| 关闭当前 tab | ✅ 清掉 |
| 关闭其他 tab | ❌ 保留 |
| 关闭右侧所有 / 全部 tab | ✅ 清掉对应 |
| 用户登出 | ✅ 全部清掉 |
| 后端动态路由刷新 | ✅ 全部清掉（路由表重建） |

手动清单个 tab 的缓存：

```typescript
import { useTabStore } from '@/store/modules/tab';

const tabStore = useTabStore();
tabStore.removeTabByRouteName('manage_user');   // 关掉对应 tab，缓存随之清掉
```

## keepAlive vs multiTab

- `keepAlive: true` — 同一路由的实例在 tab 切换中存活
- `multiTab: true` — 同一路由可以打开**多个** tab（每个独立实例）

二者可以同时启用：例如详情页 `manage_user/:id`，每个 id 都是单独的 tab，每个 tab 内部还能保留状态。

## 性能注意

并非所有页面都适合缓存：

- ✅ 列表 / 看板 / 配置类页面 — 用户切来切去想保留状态
- ❌ 详情页（如 `:id` 不同实例不同） — 用 `multiTab` 而不是 `keepAlive`
- ❌ 内嵌大型 chart 但又不一定每次都用 — 缓存会一直占内存

```typescript
// 折中：缓存但 onActivated 时丢弃重型组件状态
onActivated(() => {
  chartInstance.value?.dispose();
  initChart();
});
```

## 相关

- [路由组件](./component.md)
- [路由跳转](./push.md)
