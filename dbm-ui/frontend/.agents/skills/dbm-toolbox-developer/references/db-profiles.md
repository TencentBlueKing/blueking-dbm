# 六个 DB 的差异档案

范式六个 DB 通用，差异集中在目录名和路由名。动手前查这里，别按「应该是这样」推断。

## 命名对照

**同一个 DB 在四个地方可能有四种写法**，只有 TenDBCluster 三处不一致：

| DB | `DBTypes` 枚举 | views 目录 | details 目录 | com-factory 目录 |
| --- | --- | --- | --- | --- |
| MySQL | `mysql` | `mysql` | `mysql` | `mysql` |
| TenDBCluster | `tendbcluster` | **`tendb-cluster`** | **`tendbCluster`** | **`tendbCluster`** |
| Redis | `redis` | `redis` | `redis` | `redis` |
| SQLServer | `sqlserver` | `sqlserver` | `sqlserver` | `sqlserver` |
| MongoDB | `mongodb` | `mongodb` | `mongodb` | `mongodb` |
| Oracle | `oracle` | `oracle` | `oracle` | `oracle` |

`createToolboxRoute` 内部已做 `tendbcluster` → `tendb-cluster` 映射，组件路径不用自己拼。`createDbaToolboxRoute` 同样只这一处映射。

## 工具箱首页路由名（`routerBack` 用）

**六个各不相同，没有规律，必须查表**：

| DB | 路由 name |
| --- | --- |
| MySQL | `MysqlToolboxIndex` |
| TenDBCluster | `TendbclusterToolboxIndex` |
| Redis | `RedisToolbox` |
| SQLServer | `sqlserverToolbox`（首字母小写） |
| MongoDB | `MongoToolbox` |
| Oracle | `OracleToolbox` |

重新核对：`rg -n "name: '[A-Za-z]*[Tt]oolbox" src/views/db-manage/*/routes.ts`

**已知存量缺陷（只报告，不要顺手改）**：`SQLSERVER_ROLLBACK/Index.vue` 与 `SQLSERVER_ROLLBACK_LOCAL/Index.vue` 的
`routerBack` 指向 `SqlserverToolboxIndex`，这个路由名全仓库不存在。核实：`rg -n "SqlserverToolboxIndex" src`。

`defineExpose({ routerBack })` 在 mysql（48 处）和 tendb-cluster（42 处）是普遍写法，其余四个 DB 只有零星几处。
**新页面都该写**，不要因为同 DB 存量没写就当成「这个 DB 不需要」。

## 各 DB 一句话

`ls` 全大写目录会把**工具箱单据、服务申请、无 Index 的旧目录**混在一起。工具箱张数以 `routes.ts` 里
`createRouteItem(` 次数为准（六个合计 140）。申请页 9 个，在 `service-apply/routes.ts`。

```bash
ls -d src/views/db-manage/<views 目录>/*/ | awk -F/ '{print $(NF-1)}' | grep -E '^[A-Z][A-Z0-9_]*$'
rg -c 'createRouteItem\(' src/views/db-manage/<views 目录>/routes.ts
ls src/views/db-manage/<views 目录>/common/toolbox-field/
```

无 `Index.vue` 的旧目录（不是可进入的提单页，只报告不要顺手删）：`MYSQL_ROLLBACK_CLUSTER`、
`TENDBCLUSTER_ROLLBACK_CLUSTER`。

DBA 工具箱与 Webconsole 等非单据入口见 [dba-and-non-ticket.md](dba-and-non-ticket.md)。

- **MySQL**（38 条工具箱路由；另 2 个申请页）：范式最全，六种模式都有实例，专属列最多。存量单据见
  [inventory-mysql.md](inventory-mysql.md)，不确定新单据归哪种模式时先查那张表
- **TenDBCluster**（36 条工具箱路由；另 1 个申请页）：专属列只有 `cluster-column`，大量单据直接复用跨 DB
  公共列。三处命名不一致
- **Redis**（27 条工具箱路由；另 2 个申请页）：专属列丰富（`key-operation-column`、`regex-keys-column`、
  `target-version-select-column` 等）。申请页 `REDIS_CLUSTER_APPLY` / `REDIS_INS_APPLY` 的 `routerBack`
  带 `route.query.from` 分支，不是简单 push。唯一有 DBA 工具箱单据的 DB
- **SQLServer**（16 条工具箱路由；另 2 个申请页）：专属列只有集群 / 库名 / 表名三个
- **MongoDB**（22 条工具箱路由；另 2 个申请页）：模式拆分与跨列演算校验的范式来源。关键参考
  `MONGODB_BACKUP`（最典型表格型）、`MONGODB_SCALE_UPDOWN`（`DeepPartial` 行模型）、
  `MONGODB_EXEC_SCRIPT_APPLY`（非表格型，非 scoped 样式覆盖 `.bk-form-label`）、
  `MONGODB_INSTANCE_RELOAD`（多模式动态表格）、`MONGODB_SHARD_CUTOFF`（跨列演算校验）。
  菜单里有 `bind: [A, B]` 用法。专属列目录 `cutoff`、`addShardNodes` 是驼峰存量，新建用 kebab-case
- **Oracle**（1 条工具箱路由；无申请页）：只有 `ORACLE_EXEC_SCRIPT_APPLY`，非表格型，
  **没有 `common/toolbox-field/` 目录**
