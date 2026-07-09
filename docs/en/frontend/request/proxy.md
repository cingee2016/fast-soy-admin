# Proxy

Both the dev server and production Nginx reverse-proxy `/api/*` to FastAPI. **Use relative `/api/v1/...` paths in frontend code** to avoid hard-coding backend hosts.

## Development (Vite proxy)

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

So: browser hits `http://localhost:9527/api/v1/auth/login` → Vite proxies to `http://127.0.0.1:9999/api/v1/auth/login`.

The backend host is configurable via `web/.env.development` (to proxy to a remote backend):

```dotenv
# web/.env.development.local (gitignored)
VITE_DEV_PROXY_TARGET=http://192.168.1.10:9999
```

## Production (Nginx)

```nginx
server {
    listen 80;
    root /path/to/web/dist;

    # static assets
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API reverse proxy
    location /api/ {
        proxy_pass http://app:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket (if you have any)
    location /ws/ {
        proxy_pass http://app:9999;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

::: warning Backend must enable PROXY_HEADERS_ENABLED
Behind a reverse proxy, set in backend `.env`:

```dotenv
PROXY_HEADERS_ENABLED=true
TRUSTED_HOSTS=["10.0.0.0/8"]   # trusted upstreams
```

Otherwise [fastapi-guard](https://fastapi-guard.com/) sees every request from the nginx container's IP and bans it. See [Deployment](/en/ops/deployment).
:::

## Multi-backend / multi-service

For multiple backends (e.g. main + dashboard), configure multiple base URLs in `.env`:

```dotenv
VITE_SERVICE_BASE_URL=/api/v1
VITE_OTHER_SERVICE_BASE_URL={"report":"/report","ws":"/ws"}
```

Add corresponding Vite proxies:

```typescript
proxy: {
  '/api':    { target: 'http://app:9999', changeOrigin: true },
  '/report': { target: 'http://report:8080', changeOrigin: true },
  '/ws':     { target: 'ws://ws-server:9001', ws: true, changeOrigin: true },
}
```

Then construct a separate `request` per base URL.

## CORS troubleshooting

| Symptom | Cause |
|---|---|
| Console "blocked by CORS" | Hit a non-`/api` URL directly (bypassed proxy) |
| `Network Error` | Backend down / proxy target unreachable |
| `502 Bad Gateway` | Nginx upstream `app:9999` unreachable |
| API returns OK but frontend logs out immediately | Backend disabled OPTIONS preflight; check CORS |

Backend CORS is in `app/core/init_app.py`'s `CORSMiddleware`, default `["*"]`. Production should narrow to specific origins (`CORS_ORIGINS=["https://admin.example.com"]`).

## See also

- [Intro](/en/frontend/request/intro)
- Backend: [Deployment](/en/ops/deployment) / [Configuration](/en/ops/config)
