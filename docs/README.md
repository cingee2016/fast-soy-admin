# OPS Admin 文档规范

## 文档结构

```
docs/
├── README.md              ← 本文件：流程规范
├── overview.md            ← 项目总览/章程
├── fast-soy-admin/        ← 原始骨架文档归档
├── modules/               ← SDD 五阶段功能模块文档
│   └── <module>/          ← 每个功能模块一个文件夹
├── adr/                   ← 架构决策记录
└── superpowers/           ← brainstorming & plans
    ├── specs/
    └── plans/
```

## SDD 五阶段闭环

每个功能模块在 `docs/modules/<module>/` 下维护五阶段文档：

| 阶段 | 文件命名 | 说明 |
|------|---------|------|
| 01 | `<module>_01_requirements.md` | 需求 |
| 02 | `<module>_02_specs.md` | 规格 + API 契约 |
| 03 | `<module>_03_tests.md` | 测试用例矩阵 |
| 04 | `<module>_04_impl.md` | 实现与验收记录 |
| 05 | `<module>_05_product.md` | 产品文档（可选——验收通过后产出） |

**示例**：`docs/modules/user-auth/user-auth_01_requirements.md`

## 任务量级与文档要求

- **lightweight**（≤2 文件）：无文档要求
- **medium**（3-6 文件）：更新受影响阶段的 spec/tests 文档
- **heavy**（>6 文件或架构变更）：完整五阶段闭环

## 架构决策记录 (ADR)

存放于 `docs/adr/`，命名格式：`NNNN-<short-title>.md`

示例：`docs/adr/0001-layered-architecture.md`

## 骨架文档归档

`docs/fast-soy-admin/` 包含 FastSoyAdmin 原始骨架的完整技术文档，作为参考保留。
