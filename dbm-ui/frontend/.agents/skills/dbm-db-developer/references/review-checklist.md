# review 集群管理面改动

取改动范围、跑 eslint、缺陷门槛、P0-P3 输出格式一律走 `dbm-reviewer` skill，**本篇只列集群管理面特有的检查项**。

## 先定需求范围

改动是在加能力、加列、加菜单时，先按 [feature-scope.md](feature-scope.md) 判定全部 / 一类 / 某一个，再看 diff：

- 范围是**某一个**，却改了 `CommonColumn` / `ActionPanel` 默认 Tab → 落错层
- 范围是**全部**，却只在某一个 `{db}/` 里实现 → 其它 DB 会缺
- 把「已记录的能力」里没有的 DB 补上了（例如给 oracle 补分区）→ 除非需求写明扩名单，否则当误补
- 新开了白名单或单 DB 能力，却没在 `feature-scope.md` 加行 → 名单会过期

## 先定改动类型

| diff 主要落在 | 类型 | 重点 |
| --- | --- | --- |
| `src/common/const/` + `layout/` + 新的 `{db}/` 目录 | 接入新 DB | 全量核 [registry-map.md](registry-map.md)，重点是无编译期保障的 C、D 节 |
| `common/cluster-table/`、`common/instance-table/`、`common/cluster-details/`、`common/hooks/` | 公共组件 | 影响所有用了这套骨架的 DB（influxdb 除外），按引用点穷举 |
| 单个 `{db}/` 下的列表 / 详情 / 申请页 | 单 DB 迭代 | 先看 [feature-scope.md](feature-scope.md) 这是某一个还是该下沉的全部 / 一类 |
| `{db}/{TICKET_TYPE}/` | 不是本 skill | 转 `dbm-toolbox-developer` 的 `workflow-review.md` |
| `services/model/ticket/**`、`com-factory/**`、`useCreateTicket` / `useTicketDetail` 调用 | 不是本 skill | 转 `dbm-ticket-developer` 的 `review.md` |

## 检查项

### 登记完整性

新增 DB 或新增集群架构时，逐条比对 [registry-map.md](registry-map.md)，并跑它末尾的 `rg -il` 差集自查。
重点在 C、D 两节的「行为映射」——那些表没有编译期保障，registry-map 每条都标了漏登记的表现，照着核。

### 一致性

四处字符串必须同值，不对齐的表现全是运行时才暴露：

| 一致性 | 涉及 |
| --- | --- |
| 集群详情路由 name | `{db}/routes.ts` 的 `name` ＝ `useGoClusterDetail('...')` 入参 ＝ `clusterTypeListPageMap` 的 value |
| DB 入口路由 name | `{db}/routes.ts` 父路由 `name` ＝ `DBTypeInfos.routeIndexName` ＝ `layout/Index.vue` 的 `routeGroup` |
| 菜单跳转 | `module-group/{Db}.vue` 的 `route-name` ＝ 列表路由 `name` |
| 启停单据 key 粒度 | 页面传给 `useOperateClusterBasic` 的 `ClusterTypes` ＝ `ticketTypeMap` 的 key |
| 申请页 | `TicketTypes` 枚举值 ＝ 申请页目录名 ＝ `createApplyRoute` 的 ticketType ＝ 入口卡片的 `id` |

### 骨架与分层

- 列表页有没有绕开 `ClusterTable` 自己写 `DbTable`；详情页有没有绕开 `ActionPanel` 自己拼 Tab
  （influxdb 除外，它本来就不用公共骨架）
- 详情实现是否放在 `{db}/common/{架构}-cluster-detail/`，路由壳里有没有混进业务逻辑
- 抽屉入口与路由入口是不是同一个实现，有没有出现第二份详情
- 某个 DB 独有的列有没有被塞进 `cluster-table/CommonColumn.vue`；反过来，所有 DB 都要的列有没有在多个业务页
  各实现一遍。正确做法见 [page-skeletons.md](page-skeletons.md)「新增一列的顺序」
- 新增 slot 是否按字段名命名，与现有 slot 风格一致

### 公共组件改动

- `clusterType.includes('k8s')` 这类形态分支被删或被改判据时，能不能复述它原本在区分什么；说不清就按 P1 报
- 给公共组件加 prop 是加性的（有默认值、老调用方不用改）还是破坏性的
- 改了 `ISupportClusterType` / `ClusterTypeRelateClusterModel`，两份 `ClusterTypeRelateClusterModel`
  和 `base-info/types.ts`、`instance-table/types.ts` 是否同步
- 公共列组件里有没有混进某个 DB 的业务判断（应当通过 props 注入差异）

### 路由与开关

- `{db}/routes.ts` 导出的是不是 `getRoutes(funControllerData)`，开关关闭是否返回 `[]`
- 该 DB 的所有页面是否都挂在同一个父路由 `children` 下（父级 glob **只取 `routes[0]`**，挂在第二个顶层对象
  里的路由会被静默丢弃）
- 新增页面是否配了 `dbConsole` 开关；`v-db-console` 的 key 是否在 `FunctionController` 里声明过
- 目录名与 `DBTypes` 值不一致的 DB，`createApplyRoute` 的 `routeNameMap` 有没有跟上

### 数据层

- 集群 Model 是否 `extends ClusterBase`，有没有重复实现基类已有的 `isOnline` / `isNew` / `createAtDisplay`
- 列表接口有没有把接口级 `permission` 合并进每行
- 新 source 文件的 URL 前缀是否与同模块现有接口一致（别按 `db_type` 想当然拼）

## 人工验证清单

写进报告的「待人工验证」段，按需裁剪；新接入的 DB 全部跑一遍：

1. 后端开关打开后侧栏出现该 DB 分组，折叠态缩写正常，集群数角标正确；该业务集群数为 0 时是否还显示，
   取决于 `ClusterCountMap` 登记与调用方的 `ignoreClusterCount`
2. 集群列表：加载、搜索栏与列筛选联动、列显隐刷新后保留、导出 Excel
3. 集群详情：抽屉入口 + 独立路由页两个入口，逐个 Tab 点开
4. 行操作：启用 / 禁用 / 删除 / 重启各提一单，去单据中心确认详情页渲染正确（不是落到 `Default.vue`）
5. 改集群别名、加删集群标签
6. 申请页：入口卡片可见、域名预览前缀正确、提交成功
7. 反向入口：下架待办、我的告警订阅里点集群名能跳到详情
8. 功能开关关闭后，菜单与路由整体消失

改的是公共组件时，第 2～4 条要在**至少三个形态**各挑一个 DB 复跑（关系型 / 大数据 / K8s）。
