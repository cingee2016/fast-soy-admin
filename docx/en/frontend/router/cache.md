# Route Cache

Uses Vue's `<keep-alive>` to preserve page state — switching tabs and back **doesn't recreate the component**, so search filters, scroll position, and form input persist.

## Enable

In a backend menu declaration:

```python
{"route_name": "manage_user", "keep_alive": True, ...}
```

Or frontend route meta:

```typescript
meta: {
  keepAlive: true
}
```

## Required: defineOptions(name)

`<keep-alive>` matches by component `name`, so **every cacheable page must `defineOptions({ name: 'XXX' })`**:

```vue
<script setup lang="ts">
defineOptions({ name: 'ManageUser' });   // ✅ required
</script>
```

CLI-generated pages already have it; manual pages often forget.

## onMounted no longer fires

A cached component **doesn't** re-run `onMounted`. To refresh on each activation, use `onActivated`:

```typescript
import { onActivated, onMounted } from 'vue';

onMounted(getData);          // first load
onActivated(getData);        // every re-activation
```

For "load once, don't re-fetch on activation" — only `onMounted`.

## When the cache is cleared

| Action | Cleared? |
|---|---|
| Switch to other tab | ❌ kept |
| Close current tab | ✅ cleared |
| Close other tabs | ❌ kept |
| Close right-side / all tabs | ✅ cleared |
| Logout | ✅ all cleared |
| Backend dynamic route refresh | ✅ all cleared (route table rebuilt) |

Manually clear a single tab's cache:

```typescript
import { useTabStore } from '@/store/modules/tab';

const tabStore = useTabStore();
tabStore.removeTabByRouteName('manage_user');   // closes the tab and its cache
```

## keepAlive vs multiTab

- `keepAlive: true` — same-route instance survives tab switches
- `multiTab: true` — multiple tabs of the same route allowed (each independent)

They can be combined: e.g. `manage_user/:id` — each id is a separate tab, and each tab keeps its own state.

## Performance notes

Not every page should be cached:

- ✅ Lists / dashboards / config — users want state preserved
- ❌ Detail pages with `:id` (different instances) — use `multiTab` instead
- ❌ Heavy embedded charts that aren't needed every visit — caching keeps them in memory

```typescript
// Compromise: cache, but dispose heavy bits in onActivated
onActivated(() => {
  chartInstance.value?.dispose();
  initChart();
});
```

## See also

- [Route component](/en/frontend/router/component)
- [Router push](/en/frontend/router/push)
