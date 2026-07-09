# 代理

前端开发服务器与生产 Nginx 都把 `/api/*` 反代到 FastAPI 后端，**前端代码里始终用 `/api/v1/...` 相对路径**，避免各环境硬编码后端 host。

## 开发环境（Vite proxy）

```typescript
// web/vite.config.ts
server: {
  host: '0.0.0.0',
  port: 9527,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:9999',
      changeOrigin: true,
    }
  }
}
```

即：浏览器请求 `http://localhost:9527/api/v1/auth/login` → Vite 代理到 `http://127.0.0.1:9999/api/v1/auth/login`。

后端 host 由 `web/.env.development` 控制（代理到非本机后端时使用）：

```dotenv
# web/.env.development.local（不入仓库）
VITE_DEV_PROXY_TARGET=http://192.168.1.10:9999
```

## 生产环境（Nginx）

```nginx
server {
    listen 80;
    root /path/to/web/dist;

    # 静态资源
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反代
    location /api/ {
        proxy_pass http://app:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket（如果有）
    location /ws/ {
        proxy_pass http://app:9999;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

::: warning 后端必须开启 PROXY_HEADERS_ENABLED
反代之后必须在后端 `.env` 里：

```dotenv
PROXY_HEADERS_ENABLED=true
TRUSTED_HOSTS=["10.0.0.0/8"]   # 信任的上游
```

否则 [fastapi-guard](https://fastapi-guard.com/) 看到的请求都来自 nginx 容器 IP，会触发误封。详见 [部署](../../ops/deployment.md)。
:::

## 多后端 / 多服务

业务里同时连多个后端时，在 `.env` 配多组 base URL：

```dotenv
VITE_SERVICE_BASE_URL=/api/v1
VITE_OTHER_SERVICE_BASE_URL={"report":"/report","ws":"/ws"}
```

Vite 代理对应也加：

```typescript
proxy: {
  '/api':    { target: 'http://app:9999', changeOrigin: true },
  '/report': { target: 'http://report:8080', changeOrigin: true },
  '/ws':     { target: 'ws://ws-server:9001', ws: true, changeOrigin: true },
}
```

请求工厂里用对应 base URL 单独构造一份 `request` 即可。

## 跨域错误排查

| 现象 | 原因 |
|---|---|
| 浏览器 console "blocked by CORS" | 直接请求了非 `/api` 前缀（绕过了代理） |
| `Network Error` | 后端没启动 / Vite 代理目标不可达 |
| `502 Bad Gateway` | nginx 上游 `app:9999` 不通 |
| 接口能通但前端拿到 `Network Error` 后立刻退出登录 | 后端禁用了 OPTIONS 预检；检查 CORS 配置 |

后端 CORS 在 `app/core/init_app.py` 配的 `CORSMiddleware`，默认 `["*"]`。生产应当收敛到具体域名（`CORS_ORIGINS=["https://admin.example.com"]`）。

## 相关

- [简介](./intro.md)
- 后端：[部署](../../ops/deployment.md) / [配置](../../ops/config.md)
