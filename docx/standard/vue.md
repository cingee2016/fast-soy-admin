# Vue 书写风格

基于 [SoybeanAdmin 风格](https://docs.soybeanjs.cn) 与 `@soybeanjs/eslint-config-vue`。

## SFC 结构

```vue
<script setup lang="tsx">
// 1. import
import { ref } from 'vue';
import { useRouter } from 'vue-router';

// 2. defineOptions（声明 name，配合 keep-alive）
defineOptions({ name: 'UserList' });

// 3. props
interface Props {
  initialId?: number;
}
const props = withDefaults(defineProps<Props>(), { initialId: 0 });

// 4. emits
const emit = defineEmits<{
  refresh: [];
  select: [id: number];
}>();

// 5. hooks
const router = useRouter();

// 6. 组件逻辑
const list = ref<User[]>([]);

// 7. init
function init() { /* 数据加载 */ }

// 8. watch / watchEffect
watch(() => props.initialId, init);

// 9. lifecycle
onMounted(init);

// 10. defineExpose
defineExpose({ refresh: init });
</script>

<template>
  <div>...</div>
</template>
```

## 模板规则

- `template` 中**只能有一个根元素**（`<Transition>` 切换页面动画依赖这个）
- 使用简写：`:prop`、`@click`
- 无子元素的组件自闭合：`<MyComponent />`
- 动态指令值与字符串字面量混用时优先用模板字符串，避免 `:class="'foo ' + bar"`

## TypeScript

- `script setup lang="ts"` 是默认；需要 JSX 渲染按钮时用 `lang="tsx"`
- 用 `defineProps<{...}>` / `defineEmits<{...}>` 声明类型，**不要**写运行时 props 描述
- API 返回类型在 `web/src/typings/api/<module>.d.ts` 中维护，与后端 Schema 1:1 对应

## API 调用

- API 函数定义在 `web/src/service/api/<module>.ts`，命名 `fetchXxx`
- 在组件 / Store / hook 中调用，**不要**在组件里直接拼 URL

```ts
// service/api/user.ts
export function fetchUserList(params: Api.UserSearch) {
  return request.Post<Api.UserListResp>('/system-manage/users/search', params);
}

// views/.../index.vue
const { data, getData } = useTable({
  apiFn: fetchUserList,
  apiParams: { current: 1, size: 10 },
  // ...
});
```

## 国际化

- **不要**在模板里硬编码中文字面量
- 用 `$t('route.user-list')` / `t('common.confirm')`
- 路由名通过 `route.<key>` 自动映射到菜单标题

## 表格 / 表单

- 列表页用 `useNaivePaginatedTable`（带分页 + 列可见性 + 操作状态）
- 抽屉式编辑用 `useTableOperate`（管理 visible / mode / record）
- 详见 [Hooks / useTable](../frontend/hooks/use-table.md)

## 按钮鉴权

```vue
<NButton v-if="hasAuth('B_HR_EMP_CREATE')" @click="handleAdd">新增</NButton>
```

不建议用 `v-show`——隐藏元素仍占位会导致 UI 错位。

## 命名

- 文件 / 目录：`kebab-case`（`user-list.vue`）
- 组件名（`defineOptions.name`）：`PascalCase`（`UserList`）
- composable / hook：`camelCase` + `use` 前缀（`useTable`）
- 常量：`UPPER_SNAKE_CASE`

详见 [命名规范](./naming.md)。
