# 使用方式

API 函数定义在 [src/service/api/](../../../web/src/service/api/)，按后端模块各一个文件，命名 `fetchXxx`。

## 一个完整流程

### 1. 后端先有接口

```python
# app/business/inventory/api/manage.py
@router.post("/products/search", summary="搜索商品")
async def _(obj_in: ProductSearch): ...
```

### 2. TS 类型定义

```typescript
// web/src/typings/api/inventory-manage.d.ts
declare namespace Api {
  namespace Inventory {
    interface ProductSearch extends Common.PaginatingCommonParams {
      name?: string;
      status?: 'pending' | 'onboarding' | 'active' | 'resigned';
    }

    interface Product {
      id: string;          // sqid
      productNo: string;
      status: string;
      tenantId: string;
      tenantName: string;
      tagIds: string[];
      tagNames: string[];
      createdAt: string;
      // ...
    }

    type ProductListResp = Common.PaginatingQueryRecord<Product>;
  }
}
```

### 3. API 函数

```typescript
// web/src/service/api/inventory-manage.ts
export function fetchProductList(params: Api.Inventory.ProductSearch) {
  return request.Post<Api.Inventory.ProductListResp>('/business/inventory/products/search', params);
}

export function fetchCreateProduct(body: Api.Inventory.ProductCreate) {
  return request.Post<Api.Common.CreatedId>('/business/inventory/products', body);
}

export function fetchUpdateProduct(id: string, body: Api.Inventory.ProductUpdate) {
  return request.Patch<Api.Common.UpdatedId>(`/business/inventory/products/${id}`, body);
}

export function fetchDeleteProduct(id: string) {
  return request.Delete<Api.Common.DeletedId>(`/business/inventory/products/${id}`);
}

export function fetchBatchDeleteProducts(ids: string[]) {
  return request.Delete<Api.Common.BatchDeletedIds>('/business/inventory/products', { ids });
}
```

### 4. 在组件中调用

直接 `await`：

```typescript
const { data, error } = await fetchProductList({ current: 1, size: 10 });
if (error) {
  // 网络错误（业务码失败已被 onBackendFail 统一处理）
  return;
}
console.log(data.records);
```

或者配合 [`useTable`](../hooks/use-table.md)：

```typescript
const { data, loading, columns, pagination, getData } = useNaivePaginatedTable({
  apiFn: fetchProductList,
  apiParams: { current: 1, size: 10, name: '', status: '' },
  columns: () => [...],
});
```

## 命名规范

| 操作 | 函数名 | HTTP |
|---|---|---|
| 列表 / 搜索 | `fetchXxxList(params)` | POST `/xxx/search` |
| 单条 | `fetchXxx(id)` | GET `/xxx/{id}` |
| 创建 | `fetchCreateXxx(body)` | POST `/xxx` |
| 更新 | `fetchUpdateXxx(id, body)` | PATCH `/xxx/{id}` |
| 删除 | `fetchDeleteXxx(id)` | DELETE `/xxx/{id}` |
| 批量删除 | `fetchBatchDeleteXxx(ids)` | DELETE `/xxx` |
| 派生查询 | `fetchGetXxxTree()` / `fetchGetXxxOptions()` | GET `/xxx/tree` |
| 实例动作 | `fetchXxxAction(id, body)` | POST `/xxx/{id}/action-name` |

CLI 一键生成已经按这套约定产出；手写时也建议沿用。

## 资源 ID 是 sqid 字符串

后端所有资源 ID 是 [sqid](../../develop/sqids.md) 字符串（如 `Yc7vN3kE`），不是数字。前端**不要解码**，原样传递即可：

```typescript
const id: string = '...sqid...';
fetchUpdateProduct(id, { name: 'X' });
```

`Api.Common.CreatedId` / `UpdatedId` / `DeletedId` 等返回类型也是 `string`。

## 后端响应格式

后端统一返回 `{ code, msg, data }`。请求工厂的 `transformBackendResponse` 已经把外层剥掉，业务里拿到的就是 `data`。

```typescript
// 实际网络响应
{ "code": "0000", "msg": "OK", "data": { "records": [...], "total": 100 } }

// 业务里拿到的（typeof data）
{ records: [...], total: 100, current: 1, size: 10 }
```

## 取消请求

```typescript
import { abortRequestByMethodName } from '@/service/request';
// 在组件 onBeforeUnmount 等清理时机里
abortRequestByMethodName('fetchProductList');
```

## 相关

- [简介](./intro.md)
- [代理](./proxy.md)
- [对接后端](./backend.md)
- [Hooks / useTable](../hooks/use-table.md)
