# Request

HTTP layer built on [Alova](https://alova.js.org/) (business requests) + Axios (compat), wrapped in [src/service/](../../../web/src/service/). All modules share one config: auto-attach token, auto-refresh, route business codes to logout / modal / error toast.

## Layout

```
web/src/service/
├── api/                    # per-module fetchXxx functions
│   ├── auth.ts
│   ├── system-manage.ts
│   ├── hr-manage.ts
│   └── ...
└── request/                # generic request layer (interceptors, codes, refresh)
    └── index.ts
```

## Environment

```dotenv
# web/.env
VITE_SERVICE_BASE_URL=/api/v1                    # business base
VITE_OTHER_SERVICE_BASE_URL={"demo":"/demo"}     # other services (multi-backend)

VITE_SERVICE_SUCCESS_CODE=0000                    # success code
VITE_SERVICE_LOGOUT_CODES=2100,2101,2104,2105              # force logout
VITE_SERVICE_MODAL_LOGOUT_CODES=2102,2106             # modal then logout
VITE_SERVICE_EXPIRED_TOKEN_CODES=2103            # auto-refresh
```

Backend codes: see [Response codes](/en/reference/codes).

## Response shape (1:1 with backend)

```typescript
interface BackendResponse<T> {
  code: string;   // "0000" = success
  msg: string;    // message
  data: T;        // payload
}
```

## Request factories

`src/service/request/index.ts` provides two factories:

| Factory | Returns | Use |
|---|---|---|
| `createRequest` | `Promise<TData>` (the business `data`) | most calls |
| `createFlatRequest` | `Promise<{ data, error }>` | when you need custom error handling |

Usage:

```typescript
const request = createRequest({
  baseURL: import.meta.env.VITE_SERVICE_BASE_URL,
});

export function fetchLogin(body: { userName: string; password: string }) {
  return request.Post<Api.Auth.LoginToken>('/auth/login', body);
}
```

## Request options

```typescript
interface RequestOption {
  onRequest:               (config) => config;          // inject token / common params
  isBackendSuccess:        (response) => boolean;       // success predicate (default code === '0000')
  onBackendFail:           (response, instance) => void; // unified failure handling (modal / logout / refresh)
  transformBackendResponse:(response) => any;           // unwrap { code, msg, data } → data
  onError:                 (error) => void;             // network / 5xx
}
```

Implementation: [src/service/request/index.ts](../../../web/src/service/request/index.ts).

## Automatic behavior

| Behavior | Trigger |
|---|---|
| Auto-attach `Authorization: Bearer <token>` | every request |
| Auto-refresh token + replay | code in `VITE_SERVICE_EXPIRED_TOKEN_CODES` (default `2103`) |
| Force logout | code in `VITE_SERVICE_LOGOUT_CODES` (default `2100,2101,2104,2105`) |
| Modal then logout | code in `VITE_SERVICE_MODAL_LOGOUT_CODES` (default `2102,2106`) |
| Default error toast | other non-success codes |
| Promise reject | network / 5xx / parse error |

Business code never deals with token expiration / refresh — only the value matters.

## Multi-backend

When connecting to multiple backends (main + dashboard service), call `createRequest` once per backend, or use `VITE_OTHER_SERVICE_BASE_URL`:

```typescript
const reportRequest = createRequest({
  baseURL: import.meta.env.VITE_OTHER_SERVICE_BASE_URL.report,
});
```

See [Proxy](/en/frontend/request/proxy).

## See also

- [Usage](/en/frontend/request/usage)
- [Proxy](/en/frontend/request/proxy)
- [Connect backend](/en/frontend/request/backend)
- Backend: [API conventions](/en/develop/api) / [Response codes](/en/reference/codes)
