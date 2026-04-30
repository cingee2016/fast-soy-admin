# useTable

A data-driven table hook, **UI-agnostic** — only fetches data and manages pagination / loading. NaiveUI variants build on top of it. Business code typically uses `useNaivePaginatedTable`.

Source: `web/packages/hooks/src/use-table.ts` and `web/src/hooks/common/table/`.

## Variants

| Hook | Use |
|---|---|
| `useTable` | UI-agnostic base, data only |
| `useNaiveTable` | Adds column defs + scroll width (no pagination) |
| `useNaivePaginatedTable` | Full pagination + column visibility + loading state (**most common**) |
| `useTableOperate` | Companion state for add / edit / delete drawers / dialogs |

## Typical usage

```vue
<script setup lang="tsx">
import { fetchEmployeeList } from '@/service/api/hr-manage';
import { useNaivePaginatedTable, useTableOperate } from '@/hooks/common/table';

const { columns, columnChecks, data, loading, getData, getDataByPage, mobilePagination, searchParams, resetSearchParams }
  = useNaivePaginatedTable({
    apiFn: fetchEmployeeList,
    apiParams: {
      current: 1,
      size: 10,
      name: '',
      status: undefined,
    },
    columns: () => [
      { key: 'employeeNo', title: 'No.', align: 'center' },
      { key: 'name', title: 'Name', align: 'center' },
      { key: 'status', title: 'Status', align: 'center', render: (row) => statusTag(row.status) },
      { key: 'createdAt', title: 'Created', align: 'center' },
      {
        key: 'operate',
        title: 'Actions',
        align: 'center',
        render: (row) => (
          <div class="flex-center gap-8px">
            <NButton type="primary" ghost size="small" onClick={() => handleEdit(row.id)}>Edit</NButton>
            <NPopconfirm onPositiveClick={() => handleDelete(row.id)}>
              {{ trigger: () => <NButton type="error" ghost size="small">Delete</NButton> }}
            </NPopconfirm>
          </div>
        ),
      },
    ],
  });

const { handleAdd, handleEdit, checkedRowKeys, drawerVisible, operateType, editingData }
  = useTableOperate(data, getData);
</script>
```

## API

### apiFn

A fetch function returning `{ records, total, current, size }`. `fetchEmployeeList` hits `POST /employees/search`; the response is auto-mapped.

### apiParams

Initial query (paging + your search fields). **Reactive** — changing it triggers `getData`.

### transformer (optional)

When backend field names differ from `useTable`'s expectation:

```typescript
useNaivePaginatedTable({
  apiFn,
  apiParams,
  columns,
  transformer: (res) => ({
    data: res.data.records,
    pageNum: res.data.current,
    pageSize: res.data.size,
    total: res.data.total,
  }),
});
```

Default expects `{ records, total, current, size }` — FastSoyAdmin's `SuccessExtra` already returns this, **no transformer needed**.

### columns

Function returning column config (not an array — keeps it reactive to i18n / theme).

| Field | Use |
|---|---|
| `key` | data field name (use `operate` for action column) |
| `title` | header |
| `align` / `width` / `fixed` | passed through to NaiveUI DataTable |
| `render` | JSX / VNode custom render |

### `columnChecks`

`useNaivePaginatedTable` exposes column visibility (paired with `<TableHeaderOperation v-model:columns="columnChecks">`).

### Methods

| Method | Use |
|---|---|
| `getData()` | re-fetch with current `apiParams` (preserve page) |
| `getDataByPage(page?)` | jump to page (default 1) |
| `mobilePagination` | mobile pagination object (already wired to `apiParams`) |
| `searchParams` | v-model on the search form |
| `resetSearchParams` | reset to initial values |

## useTableOperate (CRUD kit)

```typescript
const {
  drawerVisible,        // drawer visibility
  operateType,          // 'add' | 'edit'
  editingData,          // row being edited
  checkedRowKeys,       // selected row keys (batch delete)
  handleAdd,            // open drawer in add mode
  handleEdit,           // open drawer in edit mode
  handleBatchDelete,    // call batch-delete API + refresh
  onBatchDeleted,       // post-batch-delete (clear selection)
  onDeleted,            // post-single-delete
} = useTableOperate(data, getData);
```

## Pair with permission buttons

```vue
<TableHeaderOperation v-model:columns="columnChecks" :loading="loading" @refresh="getData">
  <NButton v-if="hasAuth('B_HR_EMP_CREATE')" @click="handleAdd">Add</NButton>
  <NPopconfirm
    v-if="hasAuth('B_HR_EMP_DELETE')"
    @positive-click="handleBatchDelete">
    <template #trigger>
      <NButton :disabled="!checkedRowKeys.length">Batch delete</NButton>
    </template>
  </NPopconfirm>
</TableHeaderOperation>
```

Full sample: [HR employee list](../../../web/src/views/hr/employee/index.vue).

## CLI auto-generation

`make cli-gen-web MOD=xxx` produces a list page wired with `useNaivePaginatedTable` + `useTableOperate`, including search form, drawer, action column, and batch delete. Manual code should follow the same template.

## See also

- [Development guide](/en/getting-started/workflow) — end-to-end CRUD module
- Backend [API conventions / pagination](/en/develop/api#pagination)
