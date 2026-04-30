# 对接后端

请求工厂统一处理 token、自动刷新、按业务码路由错误。下面是各机制的细节。

## Token 处理

### 注入

`onRequest` 拦截器从 `localStorage.token` 读 token，加到请求头：

```typescript
config.headers.Authorization = `Bearer ${token}`;
```

未登录时（无 token）请求**直接发送，不带 Authorization**——后端的 `DependAuth` 会返回 `2100`。

### 存储

| 存储位置 | 内容 |
|---|---|
| `localStorage.token` | access token |
| `localStorage.refreshToken` | refresh token |
| `localStorage.userInfo` | 当前用户基础信息 + 角色 + 按钮 |

登出 / 失效时由 `auth.store` 一并清掉。

### 自动刷新

后端返回 `code === '2103'`（access token 过期）时：

1. `onBackendFail` 拦截到该码
2. 用 `localStorage.refreshToken` 调 `POST /api/v1/auth/refresh-token`
3. 拿到新 token / refreshToken，更新 `localStorage`
4. **重放原请求**（带新 token）

整个流程对业务调用透明——业务侧的 `await fetchXxx()` 拿到的就是重试后的成功响应。

### 并发请求的去重

多个并发请求同时拿到 `2103` 时，工厂内部用 mutex 保证只发一次 `refresh-token`，其他请求等同一个 promise，避免 token 被刷多次或刷出更老的版本。

## 错误码映射

由 `web/.env` 配的几组业务码控制：

| 码 | 默认 | 行为 |
|---|---|---|
| `VITE_SERVICE_SUCCESS_CODE` | `0000` | 成功，返回 data |
| `VITE_SERVICE_LOGOUT_CODES` | `2100,2101,2104,2105` | 清 token + 跳登录 |
| `VITE_SERVICE_MODAL_LOGOUT_CODES` | `2102,2106` | 弹窗 → 用户确认 → 清 token + 跳登录 |
| `VITE_SERVICE_EXPIRED_TOKEN_CODES` | `2103` | 自动刷新 + 重放 |
| 其他非 `0000` | — | 弹默认错误消息（`window.$message`） |

后端响应码全集见 [响应码](../../reference/codes.md)。

## token_version 失效

后端有"立即让旧 token 失效"机制：修改密码、模拟登录恢复、强制下线时 `INCR token_version:{uid}`，旧 token 在下一次请求时返回 `2106 SESSION_INVALIDATED`。

默认 `2106` 已纳入 `VITE_SERVICE_MODAL_LOGOUT_CODES`，前端会弹窗提示后跳登录。若希望静默登出（不弹窗），将其从 `VITE_SERVICE_MODAL_LOGOUT_CODES` 移除并追加到 `VITE_SERVICE_LOGOUT_CODES`：

```dotenv
VITE_SERVICE_LOGOUT_CODES=2100,2101,2104,2105,2106
VITE_SERVICE_MODAL_LOGOUT_CODES=2102
```

## must_change_password

`POST /api/v1/auth/login` 响应里有 `mustChangePassword: boolean`。auth store 在登录成功后判断这个字段：

```typescript
if (resp.mustChangePassword) {
  routerPush({ name: 'change-password', query: { force: 'true' } });
} else {
  toHome();
}
```

业务侧不需要处理。

## 模拟登录

`POST /api/v1/auth/impersonate/{userId}`（仅 `R_SUPER` 可用）返回的 token 含 `impersonatorId`。`/user-info` 响应里会回一个 `impersonating: true` 标志，前端据此显示"正在以 XXX 身份操作"提示并提供"退出模拟"入口（清当前 token 并用旧的 SUPER token 重新登录）。

## 自定义错误码处理

如果某接口需要业务侧自己处理失败（不让默认弹消息），用 `createFlatRequest`：

```typescript
import { createFlatRequest } from '@/service/request';

const requestFlat = createFlatRequest({ baseURL: '/api/v1' });

const { data, error } = await requestFlat.Post('/foo', body);
if (error) {
  if (error.code === '2300') {
    // 资源重复，业务自定义提示
    return;
  }
  // 其他错误透传
  throw error;
}
```

## 新增 API 速查

| 步骤 | 文件 |
|---|---|
| 1. 后端写接口 | `app/business/<x>/api/manage.py` |
| 2. TS 类型 | `web/src/typings/api/<x>-manage.d.ts` |
| 3. fetchXxx 函数 | `web/src/service/api/<x>-manage.ts` |
| 4. 在组件 / store / hook 调 | — |

1–3 步可由 `make cli-gen-all` 自动产出。详见 [开发指南](../../getting-started/workflow.md)。

## 相关

- [简介](./intro.md)
- [使用方式](./usage.md)
- 后端：[认证](../../develop/auth.md) / [响应码](../../reference/codes.md)
