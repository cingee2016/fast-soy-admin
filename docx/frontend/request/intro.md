# 请求

HTTP 层基于 [Alova](https://alova.js.org/)（业务请求）+ Axios（兼容场景），统一封装在 [src/service/](../../../web/src/service/)。所有模块共用一套：自动加 token、自动刷 token、按业务码自动路由到登出 / 弹窗 / 错误提示。

## 目录结构

```
web/src/service/
├── api/                    # 各模块的 fetchXxx 函数
│   ├── auth.ts
│   ├── system-manage.ts
│   ├── hr-manage.ts
│   └── ...
└── request/                # 通用请求层（拦截器、错误码处理、token 刷新）
    └── index.ts
```

## 环境配置

```dotenv
# web/.env
VITE_SERVICE_BASE_URL=/api/v1                    # 业务请求 base
VITE_OTHER_SERVICE_BASE_URL={"demo":"/demo"}     # 其他 service（多后端）

VITE_SERVICE_SUCCESS_CODE=0000                   # 视为成功的码
VITE_SERVICE_LOGOUT_CODES=2100,2101,2104,2105    # 直接登出
VITE_SERVICE_MODAL_LOGOUT_CODES=2102,2106        # 弹窗后登出
VITE_SERVICE_EXPIRED_TOKEN_CODES=2103            # 自动刷新 token
```

后端响应码定义见 [响应码](../../reference/codes.md)。

## 响应格式（与后端完全对应）

```typescript
interface BackendResponse<T> {
  code: string;   // "0000" 表示成功；其他详见后端响应码
  msg: string;    // 业务提示
  data: T;        // 业务数据
}
```

## 请求函数工厂

`src/service/request/index.ts` 提供两种工厂：

| 工厂 | 返回 | 用途 |
|---|---|---|
| `createRequest` | `Promise<TData>`（直接是业务 data） | 大部分业务调用 |
| `createFlatRequest` | `Promise<{ data, error }>` | 需要自定义错误处理的场景 |

使用：

```typescript
const request = createRequest({
  baseURL: import.meta.env.VITE_SERVICE_BASE_URL,
});

export function fetchLogin(body: { userName: string; password: string }) {
  return request.Post<Api.Auth.LoginToken>('/auth/login', body);
}
```

## 请求选项（可在工厂里覆盖）

```typescript
interface RequestOption {
  onRequest:               (config) => config;          // 注入 token / 公共参数
  isBackendSuccess:        (response) => boolean;       // 判定业务成功（默认看 code === '0000'）
  onBackendFail:           (response, instance) => void; // 业务失败时统一处理（弹窗 / 登出 / 刷 token）
  transformBackendResponse:(response) => any;           // 把 { code, msg, data } 拆掉，只返回 data
  onError:                 (error) => void;             // 网络错误 / 5xx
}
```

完整实现见 [src/service/request/index.ts](../../../web/src/service/request/index.ts)。

## 自动行为速查

| 行为 | 触发条件 |
|---|---|
| 自动加 `Authorization: Bearer <token>` | 全部请求 |
| 自动刷新 token + 重放原请求 | 业务码命中 `VITE_SERVICE_EXPIRED_TOKEN_CODES`（默认 `2103`） |
| 直接登出 | 业务码命中 `VITE_SERVICE_LOGOUT_CODES`（默认 `2100,2101,2104,2105`） |
| 弹窗后登出 | 业务码命中 `VITE_SERVICE_MODAL_LOGOUT_CODES`（默认 `2102,2106`） |
| 弹默认错误消息 | 其他非成功业务码 |
| Promise reject | 网络错误 / 5xx / 解析失败 |

业务里**不需要**关心 token 失效、刷新等基础设施——只关心业务返回值即可。

## 多后端

如果项目里同时连多个后端（例如主后端 + 数据看板服务），用 `createRequest` 多次构造，或在 `.env` 配 `VITE_OTHER_SERVICE_BASE_URL`：

```typescript
const reportRequest = createRequest({
  baseURL: import.meta.env.VITE_OTHER_SERVICE_BASE_URL.report,
});
```

详见 [代理](./proxy.md)。

## 相关

- [使用方式](./usage.md) — 怎么写一个 fetchXxx
- [代理](./proxy.md) — 开发 / 生产代理
- [对接后端](./backend.md) — 错误码 + token 行为
- 后端：[API 约定](../../develop/api.md) / [响应码](../../reference/codes.md)
