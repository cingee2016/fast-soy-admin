# Vue Writing Style

Based on [SoybeanAdmin's style](https://docs.soybeanjs.cn) and `@soybeanjs/eslint-config-vue`.

## SFC structure

```vue
<script setup lang="tsx">
// 1. import
import { ref } from 'vue';
import { useRouter } from 'vue-router';

// 2. defineOptions (declare name for keep-alive)
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

// 6. component logic
const list = ref<User[]>([]);

// 7. init
function init() { /* data loading */ }

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

## Template rules

- The `template` **must have a single root element** (page transitions via `<Transition>` rely on this)
- Use shorthand: `:prop`, `@click`
- Self-close components without children: `<MyComponent />`
- Prefer template literals over string concatenation when mixing dynamic + literal in directive values

## TypeScript

- `script setup lang="ts"` is the default; use `lang="tsx"` only when you need JSX renderers (e.g. button columns)
- Use `defineProps<{...}>` / `defineEmits<{...}>` for type-driven declarations; **don't** mix runtime descriptors
- API return types live in `web/src/typings/api/<module>.d.ts`, 1:1 with backend schemas

## API calls

- API functions live in `web/src/service/api/<module>.ts`, named `fetchXxx`
- Call from components / stores / hooks; **don't** assemble URLs inside components

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

## i18n

- **Don't** hard-code Chinese / English literals in templates
- Use `$t('route.user-list')` / `t('common.confirm')`
- Route names auto-map to menu titles via `route.<key>`

## Tables / forms

- List pages use `useNaivePaginatedTable` (paging + column visibility + operate state)
- Drawer-style edit uses `useTableOperate` (manages visible / mode / record)
- See [Hooks / useTable](/en/frontend/hooks/use-table)

## Button permission

```vue
<NButton v-if="hasAuth('B_HR_EMP_CREATE')" @click="handleAdd">Add</NButton>
```

`v-show` is discouraged — it still occupies layout slots when hidden.

## Naming

- File / dir: `kebab-case` (`user-list.vue`)
- Component name (`defineOptions.name`): `PascalCase` (`UserList`)
- Composable / hook: `camelCase` with `use` prefix (`useTable`)
- Constant: `UPPER_SNAKE_CASE`

See [Naming](/en/standard/naming).
