# 快速开始

## 环境准备

| 工具 | 版本 |
|------|------|
| Git | - |
| Python | >= 3.12 |
| Node.js | >= 20.0.0 |
| uv | 最新 |
| pnpm | >= 10.5 |
| make | 任意版本 |

## 获取代码

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
```

## 方式一：Docker 部署（推荐）

```bash
make up           # == docker compose up -d
```

访问 `http://localhost:1880`，服务包括：

- **Nginx** (:1880) — 前端 + API 反向代理
- **FastAPI** (:9999) — 后端 API
- **Redis** (:6379) — 缓存

```bash
make logs                  # 实时查看所有服务日志
make logs SVC=app          # 仅后端；可选 SVC=nginx|redis，TAIL=N 指定行数
make down                  # 停止并移除容器
```

## 方式二：本地开发

```bash
make install-all     # 一次性安装后端 + 前端依赖
cp .env.example .env # 复制环境变量模板，按需修改 SECRET_KEY / DB_URL / REDIS_URL 等
make initdb          # 首次初始化数据库（之后不再需要）
make dev             # 并行启动后端(:9999) 和前端(:9527)，Ctrl+C 一起停
```

分开启动也可以：

```bash
make run          # 仅后端
make web-dev      # 仅前端
```

## 下一步

- [开发指南](./workflow.md) — 从 `make cli-init` 到完整 CRUD 模块的端到端流程
- [命令参考](../reference/commands.md) — 所有 `make` 命令与对应原始命令的对照表
- [架构](./architecture.md) — 分层结构、RBAC 权限模型
- [响应码](../reference/codes.md) — 统一业务码约定

## 项目结构

```
fast-soy-admin/
├── app/                          # 后端 (FastAPI)
│   ├── __init__.py               # App 工厂、中间件、生命周期
│   ├── core/                     # 分层公共设施（CRUD、dep、中间件）
│   ├── system/                   # 内置系统模块（auth / user / role / menu）
│   ├── business/                 # 业务模块（autodiscover 自动加载）
│   │   └── hr/                   #   示例：员工/部门/标签
│   ├── cli/                      # CLI 代码生成器
│   └── utils/                    # 业务开发者的统一导入入口
├── web/                          # 前端 (Vue3 + Vite + NaiveUI)
│   └── src/
│       ├── views/                # 页面组件
│       ├── service/api/          # API 请求封装
│       ├── typings/api/          # TS 类型声明
│       ├── locales/              # i18n (zh-CN / en-US)
│       ├── router/               # 动态路由（后端下发）
│       ├── store/                # Pinia
│       └── hooks/                # Vue 组合式函数
├── deploy/                       # Docker / Nginx 配置
├── migrations/                   # Tortoise 迁移文件
├── tests/                        # 后端单元测试
├── Makefile                      # 所有常用命令的统一入口
└── docker-compose.yml
```

## 质量检查

```bash
make check-all    # 后端 + 前端所有质量检查（提交前跑）
```

细分命令：

```bash
make fmt           # 后端 ruff fix + format
make typecheck     # 后端 basedpyright
make test          # 后端 pytest
make web-lint      # 前端 eslint + oxlint
make web-typecheck # 前端 vue-tsc
```
