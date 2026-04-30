---
layout: home

hero:
  name: FastSoyAdmin
  text: 全栈后台管理模板
  tagline: FastAPI · Vue3 · TypeScript · Naive UI · UnoCSS
  image:
    src: /logo.svg
    alt: FastSoyAdmin
  actions:
    - theme: brand
      text: 快速开始
      link: /getting-started/intro
    - theme: alt
      text: GitHub
      link: https://github.com/sleep1223/fast-soy-admin
    - theme: alt
      text: 在线预览
      link: https://fast-soy-admin.sleep0.de/

features:
  - icon: "\U0001F916"
    title: AI 驱动开发
    details: 内置 CLAUDE.md + llms.txt，AI Agent 按项目规范产出代码。
  - icon: "\U0001F680"
    title: CLI 端到端生成
    details: 一条命令从模型生成前后端 CRUD，分钟级交付一张表。
  - icon: "\U0001F9E9"
    title: 业务模块自动发现
    details: 模块即插即用，互不耦合，跨模块走事件总线，可独立分库。
  - icon: "\U0001F512"
    title: 三层 RBAC + 行级权限
    details: 菜单 / API / 按钮三层鉴权，叠加行级 data_scope。
  - icon: "\U0001F4C1"
    title: 动态路由
    details: 路由由后端按角色实时下发，前端不维护权限分发。
  - icon: "\U0001F4E1"
    title: Radar 全栈追踪
    details: 实时面板查看请求 / SQL / 异常 / 权限拒绝日志。
  - icon: "\U0001F9EA"
    title: 全栈类型安全
    details: basedpyright + vue-tsc，i18n 键静态可校验。
  - icon: "\U0001F433"
    title: Docker 一键部署
    details: Nginx + FastAPI + Redis，compose up -d 即上线。
---

## 界面预览

![首页-中文](/screenshots/home-zh.png)

![首页-英文](/screenshots/home-en.png)

![性能监控-仪表盘](/screenshots/radar-dashboard.png)

![性能监控-请求列表](/screenshots/radar-requests.png)

![性能监控-SQL查询](/screenshots/radar-sql.png)

![性能监控-异常列表](/screenshots/radar-exceptions.png)
