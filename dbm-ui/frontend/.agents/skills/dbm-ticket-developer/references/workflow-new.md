# 新增一个单据类型

需求拉取、评论解读、提案生成走 `tapd-todo`。本篇只写单据纵线的实现顺序，页面骨架按入口类型另读对应 skill。

## 1. 确认要建几套

判据只有一条：**后端为每种模式分配了几个 `ticket_type`，就建几套四件套。**

独立 `ticket_type` → 各自独立的 details 类型、入口页、详情组件，严禁合并成一个页面内部切换；同一 `ticket_type`
内的子类型 → 一套四件套，入口页内部放模式选择控件。判断错了返工成本很高。

## 2. 对齐协议

协议以后端提供的 JSON 为准，**先看同 DB 最近一个单据的 `details` 形状定结构**。

**提交体与详情返回不是同一个形状**：详情会多出 `clusters` / `specs` / `instances` 等后端注入的映射。两个都要看，
一个定提交类型，一个定回填与展示的取值路径。

## 3. 先写 details 类型

提交体、回填、详情展示三处都以它为准，必须先定。位置与两步导出见 [registry.md](registry.md)。

写的时候同时回答三个问题，答不上来说明协议还没对齐：每个字段后端是必返还是可选（可选的标 `?` 并在取值处兜底）；
哪些字段参与回填（必须能从 `details` 单独还原出页面上那一列）；哪些字段要在详情页展示（必须有明确来源）。

## 4. 写入口页

工具箱提单页读 `dbm-toolbox-developer`，集群弹窗侧滑与服务申请页读 `dbm-db-developer`。提交与回填的 hook 契约不分入口，
见 [submit-and-backfill.md](submit-and-backfill.md)。

## 5. 写详情组件

见 [detail-page.md](detail-page.md)。**这步不能省**：漏了不报错，详情页静默落到 `Default.vue`，用户看到一坨原始 JSON。

## 6. 过 [checklist.md](checklist.md)

它查「有没有漏做」，逐条勾完再交。
