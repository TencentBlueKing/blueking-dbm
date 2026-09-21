---
name: dbm-ticket-developer
description: >-
  场景专属技能：DBM 单据模块（提单与单据详情）的开发、迭代与 review。覆盖 TicketTypes 登记、details 类型、
  useCreateTicket / useBatchCreateTicket / useTicketDetail 的提交与回填契约、
  com-factory 单据详情组件，横跨工具箱提单页、集群列表弹窗提单、服务申请页三类入口。
  新增或修改单据类型、改提交体 / 回填 / 单据详情展示、审查单据相关改动时使用；
  当用户询问单据四件套、details 字段协议、克隆单与「再次提单」为什么缺数据、
  单据详情页为什么落到 Default.vue 时也使用。
---

# DBM 单据开发

「单据」横跨三个模块：**在哪提** → **提交什么** → **详情怎么展示**。本 skill 管这条纵线，不管各入口页面自己的骨架。

## 三类入口，一套契约

| 入口 | 位置 | 页面骨架看 |
| --- | --- | --- |
| 工具箱提单页 | `db-manage/{db}/{TICKET_TYPE}/Index.vue` | `dbm-toolbox-developer` |
| 集群列表 / 详情的弹窗侧滑 | `db-manage/common/hooks/useOperateClusterBasic.tsx`、`machine-expansion/` 等 | `dbm-db-developer` |
| 服务申请页 | `service-apply/**` 经 `createApplyRoute` / `useApplyBase`；页面文件常在 `{db}/*_APPLY/` | `dbm-db-developer` |

页面长得完全不同，但枚举、details 类型、提交与回填 hook、详情组件是同一套。**大数据与 K8s 类 DB 没有工具箱，
但照样有单据**（启停、删除、扩容），走第二类入口。

本 skill 不管各入口页面自己的骨架（见上表第三列），需求拉取与提案生成走 `tapd-todo`。
其余 skill 分工见 `AGENTS.md`「技能索引」。

## 在做什么

| 场景 | 读哪篇 |
| --- | --- |
| 新增一个单据类型 | [workflow-new.md](references/workflow-new.md) |
| 查登记位置、目录名怎么拼 | [registry.md](references/registry.md) |
| 写提交体、写回填、排查克隆单缺数据 | [submit-and-backfill.md](references/submit-and-backfill.md) |
| 写或改单据详情组件 | [detail-page.md](references/detail-page.md) |
| **写完自检** | [checklist.md](references/checklist.md) |
| review 单据改动 | [review.md](references/review.md) |

## 单据四件套

| # | 产物 | 位置 | 缺了会怎样 |
| --- | --- | --- | --- |
| 1 | `TicketTypes` 枚举 | `common/const/ticketTypes.ts`，值与后端一致 | 后端拒单 |
| 2 | details 类型 | `services/model/ticket/details/{db}/` + 同目录 `index.ts` 导出 | `Mysql.Xxx` 取不到 |
| 3 | 提单入口 | 三类之一，组装 `details` 提交体 | 界面上没入口 |
| 4 | 详情组件 | `com-factory/{db}/{Xxx}.vue`，`defineOptions.name` **严格等于枚举值** | 静默退回 `Default.vue` |

第 4 件的 `name` 是工厂唯一的匹配依据，没有编译期保障。支持「再次提单」的还有第五件：入口页接
`useTicketDetail`，非工具箱入口另在 `TicketClone.vue` 登记路由。位置与命名对照见
[registry.md](references/registry.md)。

**改一个字段 = 四处同改**：提交体 → `details` 类型 → `useTicketDetail` 回填 → 详情组件展示列。缺一处就是 bug，
且多数不报错。

## 三个提单 hook

| hook | 用在哪 | 一句话 |
| --- | --- | --- |
| `useCreateTicket` | 绝大多数场景 | 非工具箱入口**必须传 `isToolbox: false`**，否则失败没有任何提示 |
| `useBatchCreateTicket` | 要按 `bk_biz_id` 拆成多张单 | 依赖 `route.meta.ticketType`，只有五个 DB 有结果页路由 |
| `useApplyBase` | 只有服务申请页 | 内部已封好 `useCreateTicket`，不要再建一个 |

完整契约见 [submit-and-backfill.md](references/submit-and-backfill.md)。
