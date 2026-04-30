# useTable

数据驱动的表格 Hook，**与具体 UI 库无关**——只管"调接口、维护数据 / 分页 / 加载态"。NaiveUI 适配封了三个变体在它之上。业务一般直接用 `useNaivePaginatedTable`。

源码：`web/packages/hooks/src/use-table.ts` 与 `web/src/hooks/common/table/`。

## 三个变体

| Hook | 用途 |
|---|---|
| `useTable` | UI 无关基类，纯数据 |
| `useNaiveTable` | 加列定义 + 滚动宽度（不带分页） |
| `useNaivePaginatedTable` | 完整分页 + 列可见性 + 加载态（**最常用**） |
| `useTableOperate` | 配套抽屉 / 弹窗的"新增 / 编辑 / 删除"状态管理 |

## 典型用法

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
      { key: 'employeeNo', title: '工号', align: 'center' },
      { key: 'name', title: '姓名', align: 'center' },
      { key: 'status', title: '状态', align: 'center', render: (row) => statusTag(row.status) },
      { key: 'createdAt', title: '创建时间', align: 'center' },
      {
        key: 'operate',
        title: '操作',
        align: 'center',
        render: (row) => (
          <div class="flex-center gap-8px">
            <NButton type="primary" ghost size="small" onClick={() => handleEdit(row.id)}>编辑</NButton>
            <NPopconfirm onPositiveClick={() => handleDelete(row.id)}>
              {{ trigger: () => <NButton type="error" ghost size="small">删除</NButton> }}
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

接收一个返回 `{ records, total, current, size }` 的 fetch 函数。`fetchEmployeeList` 走的是后端的 `POST /employees/search`，响应自动适配。

### apiParams

初始查询条件，包括 `current` / `size` 和你的搜索字段。**响应式**——改了里面的字段会自动触发 `getData`。

### transformer（可选）

后端响应字段名 ≠ `useTable` 期望时用：

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

默认假设响应是 `{ records, total, current, size }`——FastSoyAdmin 后端的 `SuccessExtra` 输出正是这个形状，**不需要传 transformer**。

### columns

返回列配置的函数（不是数组，方便随 i18n / 主题色等响应式重算）。

| 字段 | 用途 |
|---|---|
| `key` | 数据字段名（用 `operate` 表示自定义操作列） |
| `title` | 列头 |
| `align` / `width` / `fixed` | NaiveUI DataTable 字段，原样透传 |
| `render` | JSX / VNode 自定义渲染 |

### `columnChecks`

`useNaivePaginatedTable` 提供列可见性切换（搭配 `<TableHeaderOperation v-model:columns="columnChecks">`）。

### 返回的核心方法

| 方法 | 用途 |
|---|---|
| `getData()` | 当前 `apiParams` 重新拉一次（保留页码） |
| `getDataByPage(page?)` | 跳到指定页（不传则回到 1） |
| `mobilePagination` | 手机分页对象（已经响应式接到 `apiParams`） |
| `searchParams` | 搜索表单 v-model 用 |
| `resetSearchParams` | 重置搜索表单到初始值 |

## useTableOperate（CRUD 套件）

```typescript
const {
  drawerVisible,        // 抽屉可见
  operateType,          // 'add' | 'edit'
  editingData,          // 当前编辑的行
  checkedRowKeys,       // 选中的行 keys（批量删除用）
  handleAdd,            // 打开抽屉 + add 模式
  handleEdit,           // 打开抽屉 + edit 模式
  handleBatchDelete,    // 调批量删除接口 + 刷新
  onBatchDeleted,       // 删除后回调（清空选中）
  onDeleted,            // 单删后回调
} = useTableOperate(data, getData);
```

## 配合"权限按钮"

```vue
<TableHeaderOperation v-model:columns="columnChecks" :loading="loading" @refresh="getData">
  <NButton v-if="hasAuth('B_HR_EMP_CREATE')" @click="handleAdd">新增</NButton>
  <NPopconfirm
    v-if="hasAuth('B_HR_EMP_DELETE')"
    @positive-click="handleBatchDelete">
    <template #trigger>
      <NButton :disabled="!checkedRowKeys.length">批量删除</NButton>
    </template>
  </NPopconfirm>
</TableHeaderOperation>
```

完整样例见 [HR 模块的员工列表](../../../web/src/views/hr/employee/index.vue)。

## CLI 自动生成

`make cli-gen-web MOD=xxx` 产出的列表页已经接好 `useNaivePaginatedTable` + `useTableOperate`，含搜索表单、抽屉、操作列、批量删除。手写时也建议照抄这个模板。

## 相关

- [开发指南](../../getting-started/workflow.md) — 端到端 CRUD 模块
- 后端 [API 约定 / 分页](../../develop/api.md#分页约定)
