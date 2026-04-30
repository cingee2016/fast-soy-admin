# Deployment

## Docker Compose (recommended)

```bash
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin
docker compose up -d
```

| Service | Port | Purpose |
|---|---|---|
| nginx | 1880 | Frontend + API reverse proxy |
| app | 9999 | FastAPI backend |
| redis | 6379 | Cache |

### Logs

```bash
docker compose logs -f          # all services
docker compose logs -f app      # backend only
make logs                       # Makefile entry; supports SVC=app|nginx|redis, TAIL=N
```

### Update

```bash
git pull
docker compose down && docker compose up -d --build   # add --build for code changes (or `make rebuild`)
```

## Manual deployment

### Backend

```bash
uv sync --no-dev

# Granian (recommended; matches docker setup)
uv run granian --interface asgi --host 0.0.0.0 --port 9999 --workers 4 app:app

# Or uvicorn
uv run uvicorn app:app --host 0.0.0.0 --port 9999 --workers 4
```

::: warning Behind a reverse proxy
Set `PROXY_HEADERS_ENABLED=true` and `TRUSTED_HOSTS` so granian reconciles `X-Forwarded-For` / `X-Forwarded-Proto` and the real client IP reaches [fastapi-guard](https://fastapi-guard.com/)'s rate limiting. Otherwise every request looks like it comes from the proxy IP and gets banned.
:::

### Frontend

```bash
cd web && pnpm install && pnpm build
# Deploy dist/ to your web server
```

### Nginx

```nginx
server {
    listen 80;
    root /path/to/web/dist;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Key production checklist

- [ ] `.env` `SECRET_KEY` rotated to a secure random value (note: this also invalidates historical sqids and JWTs)
- [ ] `APP_DEBUG=false` (hides `/openapi.json` / Swagger)
- [ ] `DB_URL` switched to PostgreSQL or MySQL (with appropriate driver installed)
- [ ] `REDIS_URL` set with strong password
- [ ] `PROXY_HEADERS_ENABLED=true` + `TRUSTED_HOSTS` if behind nginx / gateway
- [ ] `CORS_ORIGINS` restricted to actual frontend origins
- [ ] Logs rotated / shipped (default goes to `logs/`, retention 30 days)
- [ ] Migrations applied: `make mm` after deploy
- [ ] Multi-worker setup verified: only the leader writes seeds (check `app:init_done` in Redis)

## See also

- [Configuration](/en/ops/config) — env vars
- [Switching DB](/en/ops/database) — drivers
- [Monitoring](/en/ops/radar) — Radar / Guard tuning
