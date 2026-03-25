# Stage 1: install dependencies (cached unless lockfile changes)
FROM node:lts-slim AS deps
WORKDIR /build/web
RUN corepack enable && corepack prepare pnpm@latest --activate
COPY web/.npmrc web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml* ./
COPY web/packages/ ./packages/
RUN pnpm install --frozen-lockfile

# Stage 2: build (cached unless source changes)
FROM deps AS build
COPY web/ .
RUN NODE_OPTIONS=--max_old_space_size=4096 pnpm build

# Stage 3: serve with nginx
FROM nginx:latest
COPY deploy/web.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/web/dist /var/www/html/fast-soy-admin
EXPOSE 80
