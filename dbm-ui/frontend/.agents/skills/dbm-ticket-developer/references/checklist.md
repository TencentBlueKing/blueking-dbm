# 单据自检清单

写完一个单据后从头到尾过一遍。**本篇是单据纵线检查项的唯一清单**，review 时也照它逐条核；
[review.md](review.md) 只补 diff 驱动的查法——命令、存量例外、定级。

只查单据纵线。入口页骨架另过 `dbm-toolbox-developer` 的 `references/checklist.md`；通用项见 `AGENTS.md`。
改已有单据时只过相关段落。

## 协议

- [ ] `ticket_type` 数量已确认，后端分配几个就建几套，没有合并成一个入口内部切换
- [ ] 协议已对齐：对照后端提供的提交 payload 与详情返回 JSON
- [ ] **提交 payload 与详情返回两份都看过**，清楚详情多出来的 `clusters` / `specs` 从哪取

## 四件套

- [ ] `TicketTypes` 枚举已注册，**键与值完全相同**，值与后端 `ticket_type` 一致
- [ ] details 类型已定义，**且在同目录 `index.ts` 导出**
- [ ] 该 details 目录首次接入时，`ticket.ts` 已加 `export type * as Xxx`
- [ ] 入口页能组装出符合协议的提交体
- [ ] 详情组件 `defineOptions.name` **严格等于**枚举值（不一致会静默退回 `Default.vue`）
- [ ] 详情组件目录选对：走资源池规格申请的放 `resource-pool-strategy/{db}/`，其余放 `{db}/`，两处没重复
- [ ] TenDBCluster 路径没写错：views 下 `tendb-cluster`，details 与 com-factory 下 `tendbCluster`

## 提交

- [ ] `useCreateTicket` 泛型是内联提交类型，**不是** `Mysql.Xxx` 等详情类型
- [ ] 非工具箱入口传了 `isToolbox: false`，否则失败时没有任何提示
- [ ] 提交体字段与协议一致，驼峰已转下划线
- [ ] 页级单选的 radio **直接绑后端枚举值**，没造前端枚举再写双向映射
- [ ] 资源标签传了 `labels` + `label_names` 两个字段，按序对应
- [ ] 提单成功后有后续动作的，判的是 `run` 返回的 `ticketId`，不是判异常
- [ ] 页面没有重复处理成功提示、重复单据确认、失败行级回填（hook 内部已做）

## 回填

- [ ] `useTicketDetail` 已接入，克隆 / 再次提单能还原页面
- [ ] **入口页每一列 / 每一个表单项都有对应赋值**，已手工逐项对照过提交体
- [ ] 重点自查资源标签（`labels` + `label_names` 组装成 `{ id, value }[]`）和规格 `spec_id`
- [ ] `clusters` / `specs` 用可选链兜底，没有直接索引
- [ ] 非工具箱单据已在 `TicketClone.vue` 的 `ticketTypeRouteNameMap` 登记目标路由（业务工具箱自动覆盖；DBA 页 `name` 带 `DBA_` 前缀，不会覆盖）

## 详情组件

- [ ] 形态选对：纯表格型 / 带页级表单项 / 模式型，展示顺序与入口页一致
- [ ] 展示字段与入口页可编辑字段一一对应，每一列都能说清来自哪个 `details` 字段，没有臆造字段名
- [ ] 空值统一 `--`；资源标签为空显示绿色「通用无标签」
- [ ] 规格名取顶层 `details.specs?.[spec_id]?.name`，不从 `resource_spec.master.spec_name` 取
- [ ] `row-key` 用行标识字段，不用后端生成的 `task_name`
- [ ] 侧滑等交互入口放在单元格上，不放表头插槽
- [ ] `TicketInfoTable` 没被显式 import（全局已注册）
