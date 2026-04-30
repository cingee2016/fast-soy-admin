# Usage

API functions live in [src/service/api/](../../../web/src/service/api/), one file per backend module, named `fetchXxx`.

## End-to-end

### 1. Backend endpoint

```python
# app/business/hr/api/manage.py
@router.post("/employees/search", summary="search employees")
async def _(obj_in: EmployeeSearch): ...
```

### 2. TS types

```typescript
// web/src/typings/api/hr-manage.d.ts
declare namespace Api {
  namespace HR {
    interface EmployeeSearch extends Common.PaginatingCommonParams {
      name?: string;
      status?: 'pending' | 'onboarding' | 'active' | 'resigned';
    }

    interface Employee {
      id: string;          // sqid
      employeeNo: string;
      status: string;
      departmentId: string;
      departmentName: string;
      tagIds: string[];
      tagNames: string[];
      createdAt: string;
    }

    type EmployeeListResp = Common.PaginatingQueryRecord<Employee>;
  }
}
```

### 3. API function

```typescript
// web/src/service/api/hr-manage.ts
export function fetchEmployeeList(params: Api.HR.EmployeeSearch) {
  return request.Post<Api.HR.EmployeeListResp>('/business/hr/employees/search', params);
}

export function fetchCreateEmployee(body: Api.HR.EmployeeCreate) {
  return request.Post<Api.Common.CreatedId>('/business/hr/employees', body);
}

export function fetchUpdateEmployee(id: string, body: Api.HR.EmployeeUpdate) {
  return request.Patch<Api.Common.UpdatedId>(`/business/hr/employees/${id}`, body);
}

export function fetchDeleteEmployee(id: string) {
  return request.Delete<Api.Common.DeletedId>(`/business/hr/employees/${id}`);
}

export function fetchBatchDeleteEmployees(ids: string[]) {
  return request.Delete<Api.Common.BatchDeletedIds>('/business/hr/employees', { ids });
}
```

### 4. Use it

Direct `await`:

```typescript
const { data, error } = await fetchEmployeeList({ current: 1, size: 10 });
if (error) {
  // network error (business failures already handled by onBackendFail)
  return;
}
console.log(data.records);
```

Or with [`useTable`](/en/frontend/hooks/use-table):

```typescript
const { data, loading, columns, pagination, getData } = useNaivePaginatedTable({
  apiFn: fetchEmployeeList,
  apiParams: { current: 1, size: 10, name: '', status: '' },
  columns: () => [...],
});
```

## Naming convention

| Operation | Function | HTTP |
|---|---|---|
| List / search | `fetchXxxList(params)` | POST `/xxx/search` |
| Single | `fetchXxx(id)` | GET `/xxx/{id}` |
| Create | `fetchCreateXxx(body)` | POST `/xxx` |
| Update | `fetchUpdateXxx(id, body)` | PATCH `/xxx/{id}` |
| Delete | `fetchDeleteXxx(id)` | DELETE `/xxx/{id}` |
| Batch delete | `fetchBatchDeleteXxx(ids)` | DELETE `/xxx` |
| Derived query | `fetchGetXxxTree()` / `fetchGetXxxOptions()` | GET `/xxx/tree` |
| Instance action | `fetchXxxAction(id, body)` | POST `/xxx/{id}/action-name` |

CLI-generated code already follows this; manual code should too.

## Resource IDs are sqid strings

Backend resource IDs are [sqid](/en/develop/sqids) strings (e.g. `Yc7vN3kE`). Frontend **does not decode** — pass through:

```typescript
const id: string = '...sqid...';
fetchUpdateEmployee(id, { name: 'X' });
```

`Api.Common.CreatedId` / `UpdatedId` / `DeletedId` are all `string`.

## Backend response

The backend returns `{ code, msg, data }`. `transformBackendResponse` strips the outer wrapper, so business code receives `data`.

```typescript
// On the wire
{ "code": "0000", "msg": "OK", "data": { "records": [...], "total": 100 } }

// In business code (typeof data)
{ records: [...], total: 100, current: 1, size: 10 }
```

## Cancel a request

```typescript
import { abortRequestByMethodName } from '@/service/request';
// e.g. in onBeforeUnmount
abortRequestByMethodName('fetchEmployeeList');
```

## See also

- [Intro](/en/frontend/request/intro)
- [Proxy](/en/frontend/request/proxy)
- [Connect backend](/en/frontend/request/backend)
- [Hooks / useTable](/en/frontend/hooks/use-table)
