# DBA 工具箱与非单据入口

业务工具箱（`createToolboxRoute` + `{db}/{TICKET_TYPE}/`）是主路径。下面两类都在工具箱产品里，但**不是**那套五件套，不要按漏登记去补 `TicketTypes` / details / com-factory。

## 先判定入口

| 入口 | 判据 | 路由怎么建 |
| --- | --- | --- |
| 业务工具箱单据 | 菜单 `id` 是 `TicketTypes.X` | `createToolboxRoute` |
| DBA 工具箱单据 | 文件在 `{db}/dba-manage/{TICKET_TYPE}/` | `createDbaToolboxRoute`，`name` 是 `DBA_${ticketType}` |
| 非单据工具 | 菜单 `id` 是普通字符串（如 `MySQLWebconsole`） | 手写 route，禁止 `createRouteItem` |
| 服务申请 | `service-apply/routes.ts` 里的 `createApplyRoute` | **不是工具箱**，走 `dbm-db-developer` |

## DBA 工具箱

挂在全局路由 `dba-manage`（`src/views/db-manage/routes.ts` 的 `dbaModules` glob），不是业务侧栏的 toolbox。
`createDbaToolboxRoute` 与 `createToolboxRoute` 一样只映射 `TENDBCLUSTER` → `tendb-cluster`。

| | 业务工具箱 | DBA 工具箱 |
| --- | --- | --- |
| helper | `createToolboxRoute` | `createDbaToolboxRoute` |
| 页面 | `{db}/{TICKET_TYPE}/Index.vue` | `{db}/dba-manage/{TICKET_TYPE}/Index.vue` |
| route `name` | 枚举值 | `DBA_${枚举值}` |
| 菜单 | `{db}/toolbox/toolboxMenuList.ts` | 该 DB `dba-manage/Index.vue` 里的 `routes` 数组（`id` 必须带 `DBA_` 前缀） |
| 再次提单 | `TicketClone` 自动命中 | **不会**命中 DBA 页 |

Redis 四个 DBA 单据与业务工具箱**共用 ticket_type、各有一份 Index.vue**。改 DBA 那份不等于改了业务那份。再次提单落到业务工具箱页，这是映射规则，不是漏登记。

现况（数字会变）：

```bash
ls src/views/db-manage/*/dba-manage
rg -n 'createDbaToolboxRoute' src/views/db-manage
```

- **Redis**：唯一调用 `createDbaToolboxRoute` 的。四个单据
  `REDIS_CLUSTER_CUTOFF` / `REDIS_PROXY_KICKOFF` / `REDIS_PROXY_FIX` / `REDIS_CLUSTER_REINSTALL_DBMON`
- **mysql / tendb-cluster**：只有手写的 `web-query`（管理控制台），路由名
  `DbaManageMysqlWebQuery` / `DbaManageTendbClusterWebQuery`
- **sqlserver**：同样只有 `web-query`（`DbaManageSQLServerWebQuery`），且没有 `toolbox-result` 子路由
- **mongodb / oracle**：没有 `dba-manage/` 目录

新增 Redis DBA 单据：页面放 `redis/dba-manage/{TICKET_TYPE}/`，用 `createDbaToolboxRoute(DBTypes.REDIS)` 注册，菜单写在 `redis/dba-manage/Index.vue`。不要复用业务工具箱那份 `Index.vue`。

## 非单据入口

菜单叶子 `id` 不是 `TicketTypes.*` 时，是查询 / 记录 / 分析页，不提单。路由手写，`name` 与菜单 `id` 一致。

| DB | 菜单叶子 `id`（= 路由 name） |
| --- | --- |
| MySQL | `MySQLWebconsole`、`MySQLMergeDiskSpace` |
| TenDBCluster | `SpiderWebconsole` |
| Redis | `RedisWebconsole`、`RedisStructureInstance`、`RedisDBDataCopyRecord`、`RedisMemoryAnalysisList`、`RedisHotKeyAnalysisList`、`RedisQueryAccessSource` |
| SQLServer | `sqlServerDataMigrateRecord` |
| MongoDB | `MongodbWebconsole`、`MongoStructureInstance`、`MongodbQueryAccessSource` |
| Oracle | 无 |

分组用的 `id`（`sql`、`copy`、`mongo_manage`）也会是字符串，不是叶子。重新核对叶子：看该项有没有 `dbConsoleValue` 且 `id` 不是 `TicketTypes.`。

单据的附属路由（开区模板创建 / 编辑、Dumper）也是手写的，不要 `createRouteItem`。
