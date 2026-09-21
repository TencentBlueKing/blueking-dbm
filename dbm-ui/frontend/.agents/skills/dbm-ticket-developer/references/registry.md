# 登记链路与命名对照

四件套靠**字符串对齐**串起来。这篇写清每件放哪、怎么导出、名字怎么拼。

## `TicketTypes` 枚举

`src/common/const/ticketTypes.ts`，当前 308 条，值与后端 `ticket_type` 完全一致。

**枚举键与值必须相同**（`MYSQL_ADD_SLAVE = 'MYSQL_ADD_SLAVE'`），全表现在零例外。不是风格问题：`TicketClone.vue`
靠 `Object.entries(TicketTypes)` 的 **key** 匹配路由 name，键值不一致的枚举项「再次提单」直接失效。

```bash
rg -o "^\s+([A-Z0-9_]+) = '([A-Z0-9_]+)'" -r '$1 $2' src/common/const/ticketTypes.ts | awk '$1 != $2'
```

## details 类型

`src/services/model/ticket/details/{目录}/`，一个单据一个 `.ts`。**两步导出，缺一步类型就取不到**：

1. 同目录 `index.ts` 加 `export * from './xxx'`（17 个目录全都有 `index.ts`）
2. 该目录首次接入时，`services/model/ticket/ticket.ts` 加 `export type * as Xxx from './details/xxx'`

两步都有编译期保障——引用方写 `TicketModel<Mysql.Xxx>`，漏了 `yarn type-check` 会报错。

**命名空间名与目录名有五处对不上**，取类型按命名空间写，建文件按目录名走：

| 命名空间（`ticket.ts` 导出名） | details 目录 | com-factory 目录 |
| --- | --- | --- |
| `Es` | `elastic-search` | `elastic-search` |
| `SurrealDB` | `surrealdb` | `surrealdb` |
| `TendbCluster` | `tendbCluster` | `tendbCluster` |
| `ResourcePool` | `resource-pool.ts`（单文件） | `resource-pool-strategy/` |
| `Bigdata` | `bigdata` | 无（大数据共用类型） |
| 其余 13 个 | 与命名空间小写同名 | 同 details 目录 |

**TenDBCluster 在 views 下是 `tendb-cluster`，在 details 与 com-factory 下是 `tendbCluster`**，最容易写错。

类型继承 `DetailBase`（`details/common.ts`），带 `__ticket_detail__` 及后端按需注入的
`clusters` / `specs` / `instances` / `machines`。这些只有后端返回才有，所以提交体不能复用详情类型，
见 [submit-and-backfill.md](submit-and-backfill.md)。

## 详情组件与工厂匹配

`src/views/ticket-center/common/ticket-detail/components/task-info/com-factory/`，387 个 `.vue`。

```ts
defineOptions({
  name: TicketTypes.MYSQL_DATA_MIGRATE,
  inheritAttrs: false,
});
```

`com-factory/Index.vue` 用两组 `import.meta.glob(eager)` 收集组件，按 `name === ticket_type` 查找：先查
`resource-pool-strategy/` 下两层，再查 `./*/*.vue` 与 `./*/*/*.vue`，都没命中落 `Default.vue`。

三条由此而来的约束：

- **glob 只到 com-factory 下两层**。`{db}/{Xxx}.vue` 和 `{db}/{子目录}/Index.vue` 都能收到，更深收不到
- **选对目录**：走资源池规格申请的放 `resource-pool-strategy/{db}/`，其余放 `{db}/`。两处都放不报错，
  会静默只生效资源池那份（两边目前**零重叠**，优先规则实际没产生分流）
- `com-factory/common/` 与 `components/` 是给子组件用的，**里面不能出现带 `TicketTypes` 名字的组件**，
  否则被工厂当详情入口收进去

## 「再次提单」的路由登记

`TicketClone.vue` 用 `ticketTypeRouteNameMap` 把 `ticket_type` 映射到目标路由，打开时带 `?ticketId=&ticketType=`，
目标页再用 `useTicketDetail` 反解。

- **工具箱单据不用登记**：`createToolboxRoute` 把路由 `name` 设成了枚举值，那份映射会自动收录
- **DBA 工具箱不用（也登记不上）**：route `name` 是 `DBA_${ticketType}`。Redis 四个 DBA 单据与业务工具箱共用
  ticket_type，再次提单落到业务那份，不是漏登记
- **其余入口手工加一行**，value 是要跳去的页面路由 name（启停类跳集群列表 `DatabaseTendbha`，授权类跳
  `PermissionRules`）。漏了按钮置灰提示「暂不支持」，不报错

入口侧还各有一处登记，不在本 skill 维护：工具箱要加提单页目录、`createToolboxRoute` 路由、`toolboxMenuList.ts`
菜单；DBA 工具箱走 `createDbaToolboxRoute`（均见 `dbm-toolbox-developer`）；集群启停 / 删除 / 重启要加
`useOperateClusterBasic` 或 `useK8sClusterRestart` 的 `ticketTypeMap`，服务申请要加 `createApplyRoute` 与入口卡片
`id`（均见 `dbm-db-developer` 的 `registry-map.md`）。

## 新增后自查

```bash
TYPE=MYSQL_YOUR_NEW_TYPE; NS=mysql; FILE=yourNewType   # NS 取 details / com-factory 目录名
CF=src/views/ticket-center/common/ticket-detail/components/task-info/com-factory
rg -n "$TYPE" src/common/const/ticketTypes.ts                          # 枚举
rg -ln "$TYPE" src/views/db-manage src/views/service-apply             # 入口
rg -n "$TYPE" $CF/$NS                                                  # 详情组件
rg -n "from './$FILE'" src/services/model/ticket/details/$NS/index.ts  # details 导出
```

任一条无输出即缺件。**details 类型本身不能用枚举值搜**——文件名是驼峰（`MYSQL_ADD_SLAVE` → `addSlave.ts`），
内容里不出现枚举字符串，所以只能查 `index.ts` 的导出行。
