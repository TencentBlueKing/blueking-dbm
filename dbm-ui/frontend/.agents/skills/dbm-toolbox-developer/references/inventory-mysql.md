# MySQL 存量单据对照表

找同类单据做参考实现、判断新单据归哪种模式时查这张表。模式定义见 [page-patterns.md](page-patterns.md)。
**新单据实现完成后同步更新本表**（模式列 + 特殊组件列）。

重新生成目录清单：

```bash
ls -d src/views/db-manage/mysql/*/ | awk -F/ '{print $(NF-1)}' | grep -E '^[A-Z][A-Z0-9_]*$'
```

| TicketType | 中文名 | 模式 | 特殊组件 |
| --- | --- | --- | --- |
| `MYSQL_ADD_SLAVE` | 添加从库 | A | `WithRelatedClustersColumn`、`MultipleResourceHostColumn`、`BackupSource` |
| `MYSQL_CHECKSUM` | 数据校验修复 | A | `MasterSlaveColumn`、`DbNameColumn`、`TableNameColumn` |
| `MYSQL_CLIENT_CLONE_RULES` | 客户端权限克隆 | A | `SourceColumn`、`TargetColumn` |
| `MYSQL_CLUSTER_STANDARDIZE` | 标准化 | A | - |
| `MYSQL_DATA_MIGRATE` | DB 数据克隆 | A | `TargetClusterColumn`（多目标）、`DataSchemaGrantColumn` |
| `MYSQL_DUMP_DATA` | 数据导出 | A | - |
| `MYSQL_DTS_DATA_MIGRATE` | DTS 同名迁移 | F | `DtsMigrateWrapper`、`TargetClusterColumn`（单目标）、`checkNotExist` 库表校验、`sync_scope` 四字段 `string[]` 协议 |
| `MYSQL_DTS_DATA_MIGRATE_RENAME` | DTS 库改名迁移 | F | `DtsMigrateWrapper`、`TargetClusterColumn`（单目标）、`DbMappingSideslider`、库映射防误清 |
| `MYSQL_FIXPOINT_EXIST_CLUSTER` | 构造（已有集群） | F | `FixpointWrapper`、`target-cluster-column`、多个子列组件 |
| `MYSQL_FIXPOINT_NEW_CLUSTER` | 构造（新集群） | F | `FixpointWrapper` |
| `MYSQL_FLASHBACK` | 回档 | C | 子类型 `RECORD_FLASHBACK` / `TABLE_FLASHBACK` |
| `MYSQL_HA_APPLY` | 主从申请 | E（服务申请，非工具箱） | 复用 `mysql/common/apply/Index.vue`；路由在 `service-apply/routes.ts` |
| `MYSQL_HA_DB_TABLE_BACKUP` | 库表备份 | A | - |
| `MYSQL_HA_FULL_BACKUP` | 全库备份 | A | `BackupLocalColumn` |
| `MYSQL_HA_TRUNCATE_DATA` | 清档（主从） | D | Wrapper + `truncate-data/` 子组件 |
| `MYSQL_IMPORT_SQLFILE` | 变更 SQL 执行 | B | 多步骤向导 `steps/step1-3` |
| `MYSQL_INSTANCE_CLONE_RULES` | DB 实例权限克隆 | A | `SourceColumn`、`TargetColumn` |
| `MYSQL_INSTANCE_FAIL_OVER` | 主库故障切换 | A | `MasterColumn`、`SlaveColumn` |
| `MYSQL_LOCAL_UPGRADE` | 版本升级（本地） | A | `CurrentVersionColumn`、`TargetVersionColumn`、`UpgradeWrapper` |
| `MYSQL_MASTER_FAIL_OVER` | 主库故障切换 | A | `MasterColumn`、`SlaveColumn` |
| `MYSQL_MASTER_SLAVE_SWITCH` | 主从互切 | A | `MasterColumn`、`SlaveColumn` |
| `MYSQL_MIGRATE_CLUSTER` | 迁移主从 | A | `cluster-migrate/`、`machine-migrate/` |
| `MYSQL_MIGRATE_SINGLE` | 单节点迁移 | A | `HostColumnGroup` + `instance-migrate/` |
| `MYSQL_MIGRATE_UPGRADE` | 版本升级（迁移） | A | `ReadonlyHostColumn` |
| `MYSQL_OPEN_AREA` | 开区模版 | A | `create/`、`template-create/` |
| `MYSQL_PROXY_ADD` | 添加 Proxy | A | `AddCountColumn`、`ProxyWrapper` |
| `MYSQL_PROXY_CONF_CHANGE` | Proxy 升降配 | A | - |
| `MYSQL_PROXY_MIGRATE` | 迁移 Proxy（按集群） | A | - |
| `MYSQL_PROXY_MIGRATE_INS` | 迁移 Proxy（按实例） | A | `InstanceColumnGroup` |
| `MYSQL_PROXY_REBUILD` | Proxy 原地重建 | A | `HostColumnGroup` |
| `MYSQL_PROXY_REDUCE` | 减少 Proxy | A | `HostColumn` |
| `MYSQL_PROXY_RESCUE` | Proxy 灾难重建 | A | `TargetCountColumn` |
| `MYSQL_PROXY_SWITCH` | 替换 Proxy | A | - |
| `MYSQL_PROXY_UPGRADE` | 版本升级（Proxy） | A | - |
| `MYSQL_RENAME_DATABASE` | DB 重命名 | A | - |
| `MYSQL_RESTORE_LOCAL_SLAVE` | 重建从库（本地） | A | - |
| `MYSQL_RESTORE_SLAVE` | 重建从库 | A | - |
| `MYSQL_ROLLBACK` | 回档（构造） | C | `CardCheckbox` 回档方式选择 |
| `MYSQL_ROLLBACK_CLUSTER` | 定点构造（旧） | A | `RollbackClusterColumn`；**目录下没有 `Index.vue`**，不是可直接进入的提单页 |
| `MYSQL_SINGLE_APPLY` | 单节点申请 | E（服务申请，非工具箱） | 复用 `mysql/common/apply/Index.vue`；路由在 `service-apply/routes.ts` |
| `MYSQL_SINGLE_TRUNCATE_DATA` | 清档（单节点） | D | Wrapper + `truncate-data/` |

41 个目录：38 个工具箱 `Index.vue` + 2 个服务申请（`MYSQL_HA_APPLY` / `MYSQL_SINGLE_APPLY`）+ 1 个无
`Index.vue`（`MYSQL_ROLLBACK_CLUSTER`）。核实日期：2026-09-21。
