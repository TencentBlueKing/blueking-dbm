---
name: dbm-db-developer
description: >-
  场景专属技能：DBM 数据库集群管理面（db 模块）的开发、迭代与 review。覆盖 15 个 DB 的集群列表、实例列表、集群详情、
  申请入口、路由与侧栏菜单（src/views/db-manage/{db}/**），以及 DB 类型在
  src/common/const、services、layout 中的登记。
  接入新 DB、给某个 DB 加集群架构（ClusterTypes）、改集群列表/详情公共组件、
  审查 db-manage 集群管理面改动时使用；
  当用户询问某个需求是所有 DB 都要、某一类 DB 要、还是某一个 DB 要，
  或询问 cluster-table / instance-table / ActionPanel 的扩展点、DBTypes 要登记到哪些表、
  各 DB 目录与路由名差异时也使用。
---

# DBM 数据库集群管理面开发

## 适用边界

本 skill 管**集群管理面**：集群列表、实例列表、集群详情、申请入口、路由与侧栏菜单，以及 DB 类型的常量登记。

| 改动落点 | 归谁 |
| --- | --- |
| `{db}/*-cluster-list`、`*-cluster-detail`、`routes.ts`、`createApplyRoute` 申请页、`common/const/` 的 DB 登记 | 本 skill |
| `{db}/{TICKET_TYPE}/` 且该类型在 `createToolboxRoute` 路由里、`toolboxMenuList.ts`、DBA / Webconsole | `dbm-toolbox-developer` |
| `services/model/ticket/**`、`com-factory/**` | `dbm-ticket-developer` |

`{db}/{TICKET_TYPE}/Index.vue` 也被申请页占用，**目录全大写不是工具箱判据**。

启停 / 删除 / 重启 / 扩缩容这类从集群列表、申请页发起的单据，**入口侧**（弹窗、确认文案、`ticketTypeMap` 登记）
归本 skill，**单据侧**（枚举、details 类型、提交体、详情组件）仍归 `dbm-ticket-developer`。

其余 skill 分工见 `AGENTS.md`「技能索引」。

## 在做什么

| 场景 | 读哪篇 |
| --- | --- |
| 接入一个新 DB | [onboarding-checklist.md](references/onboarding-checklist.md) |
| 给已有 DB 加需求、加列、加能力（先定全部 / 一类 / 某一个） | [feature-scope.md](references/feature-scope.md) |
| 给已有 DB 加集群架构、改公共组件 | [page-skeletons.md](references/page-skeletons.md) + [registry-map.md](references/registry-map.md) |
| review 集群管理面改动 | [review-checklist.md](references/review-checklist.md) |
| 查某个 DB 的目录名、路由名、ClusterTypes、开关 key | [db-matrix.md](references/db-matrix.md) |
| 查某张按 DBTypes / ClusterTypes 分发的映射表 | [registry-map.md](references/registry-map.md) |

## 核心设计：登记制，不是接口制

**页面几乎不用写，映射表必须登记全。** 一个 DB 的集群列表 / 详情 / 实例列表都复用
`src/views/db-manage/common/` 下的公共组件，各 DB 页面只是「传 `clusterType` + 传 `dataSource` + 填几个 slot」。
代价是公共组件内部靠一堆 `Record<ClusterTypes, ...>` 映射表分发，新 DB 的每种能力都要在对应的表里登记一行。

所以一个 DB 分四层，缺任何一层都是功能断裂：

| 层 | 内容 | 典型位置 |
| --- | --- | --- |
| 登记层 | `DBTypes`、`ClusterTypes`、两张 Infos 表、开关 key、profile key | `src/common/const/`、`functionController.ts` |
| 数据层 | 列表 / 详情 / 实例 / 拓扑接口 + Model 类 | `src/services/source/`、`src/services/model/` |
| 页面层 | 列表页、详情实现、详情路由壳、申请页 | `src/views/db-manage/{db}/` |
| 挂载层 | 路由、侧栏菜单组件、申请入口卡片 | `{db}/routes.ts`、`src/layout/`、`src/views/service-apply/` |

**登记层的错漏没有编译期保障。** 映射表多数是 `Record<string, X>` 或用 `as` 断言收口，少一个 key 时 TS 不报错，
运行时表现为「某个按钮点了没反应 / 某个 Tab 空白 / 跳转拿到 `name: undefined`」。逐表清单见
[registry-map.md](references/registry-map.md)，这份清单是接入和 review 共用的。

## 四类形态

接入前先判定形态，它决定复用哪套页面、要登记哪些表：

| 形态 | DB | 特征 |
| --- | --- | --- |
| 关系型 | mysql、tendb-cluster、sqlserver、oracle、mongodb | 集群 + 实例 + 主机三个维度齐全 |
| Redis | redis | 同关系型，但集群版与主从版是两套列表 / 详情 |
| 大数据 | doris、es、kafka、hdfs、pulsar、riak | 只有集群维度 + 节点角色，无实例列表页 |
| K8s | qdrant、surrealdb | 无主机 / 参数配置 / 单据记录，多出 K8s 实例列表与操作记录 |

**例外一个：influxdb 没有集群维度**，三个公共骨架一个都不用，改它只参考它自己。

形态只决定骨架。webconsole、授权、分区、CLB、Polaris、Dumper 这类**不是形态标配**，
「大数据与 K8s 没有工具箱」这类缺口也是业务设定而非遗漏。能力名单、抄哪个 DB 当样本、判定顺序**统一看**
[feature-scope.md](references/feature-scope.md)，不要凭形态推断。

## 四条不读 reference 也要记住的

1. **加需求先定范围：全部 / 一类（形态或能力白名单） / 某一个。** 没说清就问，不要按 mysql 的能力名单扩。
   「没有」默认是设定；范围是某一个却改 `common/` 默认实现，就是落错层。判定顺序见
   [feature-scope.md](references/feature-scope.md)。
2. **改 `common/cluster-table`、`common/instance-table`、`common/cluster-details` 就是改所有用了这套骨架的 DB**
   （influxdb 不用，除外）。按 `AGENTS.md` 的公共代码规则走：先 `rg -ln` 列全调用方，逐个读；
   `clusterType.includes('k8s')` 这类形态分支是全局分流判据，删之前要能说清它在区分什么。
3. **集群详情一处实现、两处入口**：实现在 `{db}/common/{架构}-cluster-detail/`，路由页是壳，列表页抽屉挂
   同一个实现。不要为抽屉另写一份，也不要在壳里写业务。
4. **`{db}/routes.ts` 导出 `getRoutes(funControllerData)`，父级 glob 只取 `routes[0]`**，
   所以一个 DB 的所有页面必须挂在同一个父路由的 `children` 下，挂在第二个顶层对象里会被静默丢弃。
