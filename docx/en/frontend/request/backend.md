# Connect Backend

The request factory handles tokens, auto-refresh, and routes business codes to actions.

## Token handling

### Inject

The `onRequest` interceptor reads `localStorage.token` and adds it to the request:

```typescript
config.headers.Authorization = `Bearer ${token}`;
```

When unauthenticated (no token) the request is **sent without Authorization** — the backend's `DependAuth` will return `2100`.

### Storage

| Location | Content |
|---|---|
| `localStorage.token` | access token |
| `localStorage.refreshToken` | refresh token |
| `localStorage.userInfo` | current user basics + roles + buttons |

`auth.store` clears all of them on logout / invalidation.

### Auto-refresh

When the backend returns `code === '2103'` (access token expired):

1. `onBackendFail` intercepts
2. POST `/api/v1/auth/refresh-token` using `localStorage.refreshToken`
3. Update `localStorage` with the new tokens
4. **Replay the original request** (with the new token)

This is transparent — `await fetchXxx()` just returns the successful retry response.

### Concurrent dedup

If multiple concurrent requests get `2103`, the factory mutex ensures only one `refresh-token` call goes out; others await the same promise. Avoids over-refreshing or replacing the new token with an even older one.

## Code mapping

Driven by `web/.env`:

| Code | Default | Behavior |
|---|---|---|
| `VITE_SERVICE_SUCCESS_CODE` | `0000` | success, return data |
| `VITE_SERVICE_LOGOUT_CODES` | `2100,2101,2104,2105` | clear token + go to login |
| `VITE_SERVICE_MODAL_LOGOUT_CODES` | `2102,2106` | modal → confirm → clear token + go to login |
| `VITE_SERVICE_EXPIRED_TOKEN_CODES` | `2103` | auto-refresh + replay |
| Other non-`0000` | — | default error toast (`window.$message`) |

Full backend codes: [Response codes](/en/reference/codes).

## token_version invalidation

Backend has a "kill old tokens immediately" mechanism: on password change, impersonation exit, or forced logout, it `INCR`s `token_version:{uid}`; old tokens fail with `2106 SESSION_INVALIDATED` on next request.

`2106` is now part of `VITE_SERVICE_MODAL_LOGOUT_CODES` by default, so the frontend confirms via modal then logs out. For silent logout (no modal), move it from `VITE_SERVICE_MODAL_LOGOUT_CODES` into `VITE_SERVICE_LOGOUT_CODES`:

```dotenv
VITE_SERVICE_LOGOUT_CODES=2100,2101,2104,2105,2106
VITE_SERVICE_MODAL_LOGOUT_CODES=2102
```

## must_change_password

`POST /api/v1/auth/login` returns `mustChangePassword: boolean`. The auth store checks it after login:

```typescript
if (resp.mustChangePassword) {
  routerPush({ name: 'change-password', query: { force: 'true' } });
} else {
  toHome();
}
```

Business code doesn't deal with this.

## Impersonate

`POST /api/v1/auth/impersonate/{userId}` (super-admin only) returns a token containing `impersonatorId`. `/user-info` includes `impersonating: true` so the frontend shows "operating as XXX" with an "exit impersonation" button (clears current token and re-logs the original SUPER token).

## Custom error handling

For endpoints that handle failures themselves (no default toast), use `createFlatRequest`:

```typescript
import { createFlatRequest } from '@/service/request';

const requestFlat = createFlatRequest({ baseURL: '/api/v1' });

const { data, error } = await requestFlat.Post('/foo', body);
if (error) {
  if (error.code === '2300') {
    // duplicate; custom message
    return;
  }
  throw error;
}
```

## Adding a new API

| Step | File |
|---|---|
| 1. Backend endpoint | `app/business/<x>/api/manage.py` |
| 2. TS types | `web/src/typings/api/<x>-manage.d.ts` |
| 3. fetchXxx function | `web/src/service/api/<x>-manage.ts` |
| 4. Use in component / store / hook | — |

Steps 1–3 can be auto-generated via `make cli-gen-all`. See [Development](/en/getting-started/workflow).

## See also

- [Intro](/en/frontend/request/intro)
- [Usage](/en/frontend/request/usage)
- Backend: [Auth](/en/develop/auth) / [Response codes](/en/reference/codes)
