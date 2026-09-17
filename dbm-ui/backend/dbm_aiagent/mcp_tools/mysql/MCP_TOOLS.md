# MySQL MCP 工具集说明（提单类）

> 来源：`backend/dbm_aiagent/mcp_tools/mysql/views/mysql_bill_mcp.py`
> 命名空间：`mysql_bill`（所有工具均通过 `name_prefix="mysql_bill"` 注册）
> 权限：`McpTicketToolPermission`，按集群粒度鉴权（`mcp_auth_parser=auth_parse_clusters`）
> 标签：所有工具均为 `READ` + `WRITE`（提单属于读写操作）
> MCP 分组：`DBMMcpTools.MYSQL_BILL`（mysql-bill）

## 公共说明

- 所有工具均为**提单类**接口：创建 DBM 单据后返回 `bills` 列表（`bill_id` + `bill_url`），实际执行需用户在 DBM 平台完成单据审批/执行。
- `bill_url` 链接格式：业务维度单据管理页 `{BK_SAAS_HOST}/{bk_biz_id}/ticket-business-manage/{ticket_id}`（如 `https://dbm.woa.com/5016766/ticket-business-manage/2382071`）。
- 集群前置校验：接口内通过 `assert_cluster_type` 校验集群类型，不支持的集群类型直接报错，不产生单据。
- 用户身份：从 `request.user.username` 获取提单人，为空时报错。
- 输出结构统一为 `SubmitBillOutputSerializer`：

```json
{
  "bills": [
    {"bill_id": 123, "bill_url": "https://dbm.woa.com/#/tickets/detail/123"}
  ]
}
```

## 工具一览

| # | 工具方法（operation_id 后缀） | 用途 | 支持的集群类型 |
|---|---|---|---|
| 1 | `submit_bill_mysql_full_backup` | 创建全备单据 | TenDBHA / TenDBCluster |
| 2 | `submit_bill_mysql_db_table_backup` | 创建库表备单据 | TenDBHA / TenDBCluster |
| 3 | `submit_bill_mysql_apply_priv` | 创建权限申请单据 | TenDBSingle / TenDBHA / TenDBCluster |
| 4 | `submit_bill_mysql_standardize` | 创建标准化单据 | TenDBSingle / TenDBHA / TenDBCluster |
| 5 | `submit_bill_mysql_db_rename` | 创建 DB 重命名单据 | TenDBSingle / TenDBHA / TenDBCluster |
| 6 | `submit_bill_tdbctl_upgrade` | 创建 TenDBCluster 中控（tdbctl）升级单据 | TenDBCluster |
| 7 | `submit_bill_proxy_replace` | 创建 TenDBHA proxy 新机替换单据 | TenDBHA |
| 8 | `submit_bill_backend_slave_replace` | 创建 TenDBHA 存储 slave 新机替换单据 | TenDBHA |
| 9 | `submit_bill_spider_replace` | 创建 TenDBCluster spider 新机替换单据 | TenDBCluster |
| 10 | `submit_bill_remote_slave_replace` | 创建 TenDBCluster remote slave 新机替换单据 | TenDBCluster |
| 11 | `submit_bill_tendbha_master_slave_switch` | 创建 TenDBHA 主从互切单据 | TenDBHA |
| 12 | `submit_bill_tendbcluster_master_slave_switch` | 创建 TenDBCluster 主从互切单据 | TenDBCluster |
| 13 | `submit_bill_mysql_construct_rollback` | 创建数据构造到已有集群 / 回档单据 | TenDBHA / TenDBCluster |
| 14 | `submit_bill_mysql_clone_grants` | 创建 DB 权限克隆流程 | TenDBSingle / TenDBHA / TenDBCluster |
| 15 | `submit_bill_mysql_disable` | **创建 MySQL 集群禁用单据（新增）** | TenDBSingle / TenDBHA / TenDBCluster |
| 16 | `submit_bill_mysql_destroy` | **创建 MySQL 集群删除单据（新增，需集群已禁用）** | TenDBSingle / TenDBHA / TenDBCluster |
| 17 | `submit_bill_proxy_conf_change` | 创建 TenDBHA proxy 升降配单据（多行，每行一个代表集群，同机关联集群自动合并） | TenDBHA |
| 18 | `submit_bill_tendbha_migrate` | 创建 TenDBHA 主从迁移单据（多行，每行一个集群或机器组） | TenDBHA |
| 19 | `submit_bill_spider_conf_change` | 创建 TenDBCluster 接入层（spider）升降配单据（多行） | TenDBCluster |
| 20 | `submit_bill_tendbcluster_node_rebalance` | 创建 TenDBCluster 集群容量变更单据（多行） | TenDBCluster |
| 21 | `submit_bill_tendbcluster_fullbackup` | 创建 TenDBCluster 全库备份单据（默认 RemoteDR 物理备份） | TenDBCluster |
| 22 | `submit_bill_spider_rebuild` | 创建 TenDBCluster 接入层（spider）原地重建单据 | TenDBCluster |
| 23 | `submit_bill_tendbcluster_slave_rebuild` | 创建 TenDBCluster slave 原地重建单据 | TenDBCluster |
| 24 | `submit_bill_tendbcluster_migrate` | 创建 TenDBCluster 主从迁移单据（多行，每行一对 remote 主从） | TenDBCluster |
| 25 | `submit_bill_proxy_rebuild` | 创建 TenDBHA proxy 原地重建单据 | TenDBHA |
| 26 | `submit_bill_tendbha_slave_rebuild` | 创建 TenDBHA 存储 slave 原地重建单据（在原机重建，不申请新资源） | TenDBHA |

## `submit_bill_mysql_full_backup`：创建 MySQL 全库备份单据

**用途**：对一个或多个 TenDBHA / TenDBCluster 集群发起全库备份，默认物理备份、slave 节点、保存 1 个月。

**operation_id**：`mysql_bill_submit_bill_mysql_full_backup`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_biz_id` | int | 是 | 业务 ID |
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，需同一集群类型） |
| `backup_type` | string | 否（默认 `physical`） | 备份类型：`physical`=物理备份，`logical`=逻辑备份 |
| `backup_local` | string | 否（默认 `slave`） | 备份位置：`master`=主节点，`slave`=从节点 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的全库备份单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 支持一次传入多个集群，但必须为同一集群类型（全 TenDBHA 或全 TenDBCluster），混合类型直接报错，不产生单据。
- 按集群类型自动选择单据类型：

| 集群类型 | TicketType | 单据名称 |
|---|---|---|
| TenDBHA | `MYSQL_HA_FULL_BACKUP` | MySQL 全库备份 |
| TenDBCluster | `TENDBCLUSTER_FULL_BACKUP` | TenDB Cluster 全库备份 |

- 所有集群按 `bk_biz_id` + `cluster_domains` 匹配；未找到的集群显式报错，不产生单据。
- 备份保存时间固定为 1 个月（`file_tag=DBFILE1M`）。
- 单据 `details` 结构：`{"backup_type": <backup_type>, "file_tag": "DBFILE1M", "infos": [{"cluster_id": ..., "backup_local": <backup_local>}, ...]}`，并通过对应 `DetailSerializer`（`MySQLFullBackupDetailSerializer` / `TenDBClusterFullBackUpDetailSerializer`）校验集群状态与备份位置。

**调用示例**（`dbm-mcp-cli`）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_mysql_full_backup \r
  body_param='{"bk_biz_id": 918, "cluster_domains": ["gamedb.test0.mysql.db", "gamedb.test1.mysql.db"]}' \r
  --raw-query "对 gamedb.test0.mysql.db 和 gamedb.test1.mysql.db 做物理备份"
```

**注意事项**

- 不传 `backup_type` 时默认物理备份（`physical`），不传 `backup_local` 时默认从节点（`slave`）。
- 全库备份为写操作，提交后需用户在 DBM 平台审批执行。

---

## `submit_bill_mysql_disable`：创建 MySQL 集群禁用单据

**用途**：对指定业务下的一个或多个 MySQL 系列集群发起禁用操作，按集群类型自动拆分生成对应禁用单据。

**operation_id**：`mysql_bill_submit_bill_mysql_disable`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_biz_id` | int | 是 | 业务 ID |
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，可混合不同类型） |
| `force` | bool | 否（默认 `false`） | 是否强制禁用（对应单据 `force` 字段） |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的禁用单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 按集群类型自动拆分提单，一个请求可能生成多张单据：

| 集群类型 | TicketType | 单据名称 |
|---|---|---|
| TenDBHA | `MYSQL_HA_DISABLE` | MySQL 高可用禁用 |
| TenDBSingle | `MYSQL_SINGLE_DISABLE` | MySQL 单节点禁用 |
| TenDBCluster | `TENDBCLUSTER_DISABLE` | TenDB Cluster 集群禁用 |

- 所有集群按 `bk_biz_id` + `cluster_domains` 匹配；未找到任何集群时报错，不产生单据。
- 传入不支持的类型（如 redis / mongodb 集群）时报错，不产生单据。
- 单据 `details` 结构：`{"cluster_ids": [...], "force": <force>}`，并通过对应 `DetailSerializer`（`MysqlHADisableDetailSerializer` / `MysqlSingleDisableDetailSerializer` / `TendbDisableDetailSerializer`）做集群状态转移等校验。

**调用示例**（`dbm-mcp-cli`）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_mysql_disable \
  body_param='{"bk_biz_id": 123, "cluster_domains": ["ha1.db.com", "cluster1.db.com"], "force": false}' \
  --raw-query "禁用集群 ha1.db.com 和 cluster1.db.com"
```

**注意事项**

- 禁用为高风险写操作，提交后需用户在 DBM 平台审批执行。
- **集群名前缀限制**：仅允许 `spider.temp` 或 `tmpdb.` 前缀的临时集群禁用，其他域名直接报错，不产生单据。
- **集群状态限制**：仅允许状态为正常（`normal`）的集群提单禁用，状态异常（`abnormal`）的集群直接报错，不产生单据。
- `force=false` 时仅对状态可转移的集群生效；`force=true` 会跳过部分状态校验。
- 一个请求混合多种集群类型时，会按类型生成多张单据，需逐一确认。

---

## `submit_bill_mysql_destroy`：创建 MySQL 集群删除单据

**用途**：对指定业务下**已禁用**的一个或多个 MySQL 系列集群发起删除操作，按集群类型自动拆分生成对应删除单据。

**operation_id**：`mysql_bill_submit_bill_mysql_destroy`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_biz_id` | int | 是 | 业务 ID |
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，可混合不同类型） |
| `force` | bool | 否（默认 `false`） | 是否强制删除（对应单据 `force` 字段） |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的删除单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- **前置条件：集群必须处于禁用状态（`phase == offline`）才可以提交删除单据**。存在未禁用集群时直接报错，不产生任何单据。状态转移规则：ONLINE(在线) → OFFLINE(禁用) → DESTROY(删除)。
- 按集群类型自动拆分提单，一个请求可能生成多张单据：

| 集群类型 | TicketType | 单据名称 |
|---|---|---|
| TenDBHA | `MYSQL_HA_DESTROY` | MySQL 高可用删除 |
| TenDBSingle | `MYSQL_SINGLE_DESTROY` | MySQL 单节点删除 |
| TenDBCluster | `TENDBCLUSTER_DESTROY` | TenDB Cluster 集群销毁 |

- 所有集群按 `bk_biz_id` + `cluster_domains` 匹配；未找到任何集群时报错，不产生单据。
- 传入不支持的类型（如 redis / mongodb 集群）时报错，不产生单据。
- 单据 `details` 结构：`{"cluster_ids": [...], "force": <force>}`，并通过对应 `DetailSerializer`（`MysqlHADestroyDetailSerializer` / `MysqlSingleDestroyDetailSerializer` / `TendbDestroyDetailSerializer`）做集群状态转移等二次校验。

**调用示例**（`dbm-mcp-cli`）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_mysql_destroy \
  body_param='{"bk_biz_id": 123, "cluster_domains": ["ha1.db.com", "cluster1.db.com"], "force": false}' \
  --raw-query "删除集群 ha1.db.com 和 cluster1.db.com"
```

**注意事项**

- 删除为高风险写操作，提交后需用户在 DBM 平台审批执行。
- **集群名前缀限制**：仅允许 `spider.temp` 或 `tmpdb.` 前缀的临时集群删除（与禁用一致），其他域名直接报错，不产生单据。
- `force` 只影响删除单据内部的状态转移校验，不豁免「必须已禁用」的前置检查；集群未禁用时即使 `force=true` 也会报错。
- 一个请求混合多种集群类型时，会按类型生成多张单据，需逐一确认。

---

## `submit_bill_proxy_conf_change`：创建 TenDBHA proxy 升降配单据

**用途**：对一批 TenDBHA 集群的 proxy 层做升降配，支持多行，每行一个代表集群（同机关联集群自动合并）。

**operation_id**：`mysql_bill_submit_bill_proxy_conf_change`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `infos[]` | object[] | 是 | 升降配信息，每行一个代表集群 |
| `infos[].cluster_domain` | string | 是 | 集群域名（代表集群） |
| `infos[].target_spec_id` | int | 是 | 目标规格 ID |
| `infos[].labels` | string[] | 否（默认 `[]`） | 资源标签 ID 列表 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的升降配单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 每行一个代表集群（`cluster_domain` + `target_spec_id` + `labels`），同机关联集群自动合并。
- 升降配是整机维度操作：同一台 proxy 机器上的多个端口实例按「机器」去重，`origin_proxies` 的 `port` 统一置 `0`，`target_proxies.count` 为去重后的机器数。
- 自动补齐同机关联集群：只提交一个代表集群时，底层会自动反查该机器上的全部同机共享集群（proxy 机器集合完全一致），合并为同一行提单，`cluster_ids` 传全。同机共享集群共享同一 `target_spec_id` 与 `labels`。
- 目标规格统一校验（存在 + 启用 + proxy 类型）；`labels` 随每行资源申请参数生效。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_proxy_conf_change \
  body_param='{"infos": [{"cluster_domain": "ha1.db.com", "target_spec_id": 12, "labels": ["1"]}]}' \
  --raw-query "对 ha1.db.com 的 proxy 升降配到规格 12"
```

---

## `submit_bill_tendbha_migrate`：创建 TenDBHA 主从迁移单据

**用途**：对一批 TenDBHA 集群做主从迁移，支持多行，每行一个集群或机器组 + 独立规格/数量/标签。

**operation_id**：`mysql_bill_submit_bill_tendbha_migrate`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `infos[]` | object[] | 是 | 迁移信息，每行一个集群或机器组 |
| `infos[].cluster_domain` | string | 是 | 集群域名 |
| `infos[].spec_id` | int | 是 | 目标规格 ID |
| `infos[].count` | int | 否（默认 `1`） | 机器组数（1组=1主+1从） |
| `infos[].labels` | string[] | 否（默认 `[]`） | 资源标签 ID 列表 |
| `opera_object` | string | 是 | 迁移类型：`cluster`=集群迁移，`machine`=整机迁移 |
| `backup_source` | string | 否（默认 `remote`） | 备份源 |
| `need_checksum` | bool | 否（默认 `true`） | 执行前是否数据校验 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的迁移单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- `spec_id` / `count` / `labels` 每行独立；`opera_object` / `backup_source` / `need_checksum` 整单共用。
- 目标规格按 backend 存储类型校验（存在 + 启用）。
- 两种迁移类型的行为差异：

| opera_object | 迁移类型 | `infos` 行粒度 | `cluster_ids` |
|---|---|---|---|
| `cluster` | 集群迁移 | 每集群一行 | 单集群 `[id]` |
| `machine` | 整机迁移 | 每「master + standby slave」机器组一行 | 该机器组承载的全部同机关联集群 |

- `machine`（整机迁移）会按 `(master_host_id, slave_host_id)` 聚合：master 与 standby slave 机器组合完全一致的集群合并为一行；只提交一个代表集群时，底层自动补齐同机关联集群并继承该组的 `spec_id` / `count` / `labels`。
- 同一机器组内 `spec_id` / `count` / `labels` 必须一致，否则报错。

**调用示例**

```bash
# 集群迁移：只迁移目标集群
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_tendbha_migrate \
  body_param='{"infos": [{"cluster_domain": "ha1.db.com", "spec_id": 12, "count": 1}], "opera_object": "cluster"}' \
  --raw-query "对 ha1.db.com 做集群迁移"

# 整机迁移：主机关联的所有集群一并迁移
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_tendbha_migrate \
  body_param='{"infos": [{"cluster_domain": "ha1.db.com", "spec_id": 12, "count": 1}], "opera_object": "machine"}' \
  --raw-query "对 ha1.db.com 做整机迁移"
```

---

## `submit_bill_spider_conf_change`：创建 TenDBCluster 接入层升降配单据

**用途**：对一批 TenDBCluster 集群的接入层（spider）做升降配，支持多行，每行一个集群 + 一个角色。

**operation_id**：`mysql_bill_submit_bill_spider_conf_change`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `infos[]` | object[] | 是 | 升降配信息，每行一个集群 |
| `infos[].cluster_domain` | string | 是 | 集群域名 |
| `infos[].spider_role` | string | 是 | 接入层角色：`spider_master`=主接入层，`spider_slave`=从接入层 |
| `infos[].target_spec_id` | int | 是 | 目标规格 ID |
| `infos[].labels` | string[] | 否（默认 `[]`） | 资源标签 ID 列表 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的升降配单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 升降配是整集群操作，同一集群只能出现一行（锁定单一 spider 角色），否则 flow 侧重复集群校验会拦截。
- 目标规格按 proxy（spider 映射为 proxy）类型校验（存在 + 启用）。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_spider_conf_change \
  body_param='{"infos": [{"cluster_domain": "spider1.db.com", "spider_role": "spider_master", "target_spec_id": 12}]}' \
  --raw-query "对 spider1.db.com 的 spider_master 升降配到规格 12"
```

---

## `submit_bill_tendbcluster_node_rebalance`：创建 TenDBCluster 集群容量变更单据

**用途**：对一批 TenDBCluster 集群做容量变更（remote 节点扩缩容），支持多行，每行一个集群 + 目标规格 + 机器组数。

**operation_id**：`mysql_bill_submit_bill_tendbcluster_node_rebalance`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `infos[]` | object[] | 是 | 容量变更信息，每行一个集群 |
| `infos[].cluster_domain` | string | 是 | 集群域名 |
| `infos[].spec_id` | int | 是 | 目标规格 ID |
| `infos[].count` | int | 否（默认 `1`） | 目标机器组数 |
| `infos[].labels` | string[] | 否（默认 `[]`） | 资源标签 ID 列表 |
| `backup_source` | string | 否（默认 `remote`） | 备份源 |
| `need_checksum` | bool | 否（默认 `true`） | 执行前是否数据校验 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的容量变更单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 集群总分片数（`cluster_shard_num`）由工具从 db_meta 自动查询，固定不变；单机分片数 = 总分片数 / 机器组数，要求 `count` 能整除总分片数。
- 目标规格按 remote（backend 存储类型）校验（存在 + 启用）。
- `prev_cluster_spec_name` / `prev_machine_pair` / 变更前规格由工具自动填充。
- 该工具**不支持** `is_safe` 参数，安全模式固定开启（与 proxy/spider 升降配、主从迁移一致）。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_tendbcluster_node_rebalance \
  body_param='{"infos": [{"cluster_domain": "spider1.db.com", "spec_id": 12, "count": 2}]}' \
  --raw-query "对 spider1.db.com 做容量变更到 2 组机器"
```

---

## `submit_bill_tendbcluster_fullbackup`：创建 TenDBCluster 全库备份单据

**用途**：对一个或多个 TenDBCluster 集群发起全库备份，默认物理备份、RemoteDR（remote slave）节点、保存 1 个月。

**operation_id**：`mysql_bill_submit_bill_tendbcluster_fullbackup`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_biz_id` | int | 是 | 业务 ID |
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，需同为 TenDBCluster） |
| `backup_type` | string | 否（默认 `physical`） | 备份类型：`physical`=物理备份，`logical`=逻辑备份 |
| `backup_local` | string | 否（默认 `slave`） | 备份位置：`slave`=RemoteDR（remote slave），`master`=remote master |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的全库备份单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 支持一次传入多个集群，但必须同为 TenDBCluster 类型，混合类型直接报错，不产生单据。
- `cluster_domains` 为空时显式报错，不产生单据。
- 按 `bk_biz_id` + `cluster_domains` 匹配；未找到的集群显式报错，不产生单据。
- 备份保存时间固定为 1 个月（`file_tag=DBFILE1M`）。
- 单据 `details` 结构：`{"backup_type": <backup_type>, "file_tag": "DBFILE1M", "infos": [{"cluster_id": ..., "backup_local": <backup_local>}, ...]}`，并通过 `TenDBClusterFullBackUpDetailSerializer` 校验集群状态与备份位置。
- **幂等防重**：在 5 分钟窗口内，同一 `creator` + `bk_biz_id` + 相同集群集合的未完结单据（含 `PENDING`/审批/待执行/执行中/失败待处理等状态）已存在时，直接复用该单据并返回其 `bill_id`，不会重复提单。

**调用示例**（`dbm-mcp-cli`）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_tendbcluster_fullbackup \
  body_param='{"bk_biz_id": 918, "cluster_domains": ["spider.test.mysql.db"]}' \
  --raw-query "对 spider.test.mysql.db 做物理备份"
```

---

## `submit_bill_spider_rebuild`：创建 TenDBCluster 接入层原地重建单据

**用途**：对一批 TenDBCluster 集群的接入层（spider）实例做原地重建，按 `(cluster_id, spider_role)` 分组。

**operation_id**：`mysql_bill_submit_bill_spider_rebuild`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，需同为 TenDBCluster） |
| `ips` | string[] | 是 | 待重建的 spider 实例 IP 列表 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的原地重建单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 仅支持接入层角色（`spider_master` / `spider_slave`），不支持 `spider_ctl` / `spider_mnt` 等非接入层角色，遇到即报错。
- `ips` 为空时显式报错，不产生单据。
- 每个 IP 必须能反查到 spider 实例；未找到的 IP 显式报错，不产生单据。
- 反查所有 spider 实例承载集群的并集必须等于输入集群，不一致时显式报错（列出缺少/多余项），防止跨集群 IP 被静默丢弃。
- 按 `(cluster_id, spider_role)` 分组生成 `infos`，每个集群的每个角色一行，`spider_ip_list` 为该角色下待重建的 spider 实例列表。
- **幂等防重**：在 5 分钟窗口内，同一 `creator` + `bk_biz_id` + 相同 `(cluster_id, spider_role, ip 集合)` 的未完结单据已存在时，直接复用该单据并返回其 `bill_id`，不会重复提单。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_spider_rebuild \
  body_param='{"cluster_domains": ["spider.test.mysql.db"], "ips": ["192.168.1.10"]}' \
  --raw-query "对 spider.test.mysql.db 的 spider 实例 192.168.1.10 原地重建"
```

---

## `submit_bill_tendbcluster_slave_rebuild`：创建 TenDBCluster slave 原地重建单据

**用途**：对一批 TenDBCluster 集群的 remote slave 实例做原地重建，按实例（ip:port）展开。

**operation_id**：`mysql_bill_submit_bill_tendbcluster_slave_rebuild`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，需同为 TenDBCluster） |
| `ips` | string[] | 是 | 待重建的 remote slave 实例 IP 列表 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的原地重建单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 每个 IP 必须能反查到 remote slave 实例；未找到的 IP 显式报错，不产生单据。
- `ips` 为空时显式报错，不产生单据。
- 一台 remote 机器上可能存在多个分片的 slave 实例（不同端口），按实例（ip:port）逐行展开。
- 反查所有 slave 实例承载集群的并集必须等于输入集群，不一致时显式报错（列出缺少/多余项）。
- 备份源固定为 `remote`，`force` 固定为 `false`（不对外暴露跳过检查开关）。
- **幂等防重**：在 5 分钟窗口内，同一 `creator` + `bk_biz_id` + 相同 `(cluster_id, ip, port)` 集合的未完结单据已存在时，直接复用该单据并返回其 `bill_id`，不会重复提单。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_tendbcluster_slave_rebuild \
  body_param='{"cluster_domains": ["spider.test2.mysql.db"], "ips": ["192.168.1.11"]}' \
  --raw-query "对 spider.test2.mysql.db 的 remote slave 实例 192.168.1.11 原地重建"
```

---

## `submit_bill_tendbcluster_migrate`：创建 TenDBCluster 主从迁移单据

**用途**：对一批 TenDBCluster 集群的 remote 主从（一主一从整组）发起主从迁移，迁移到目标规格的新机器组。

**operation_id**：`mysql_bill_submit_bill_tendbcluster_migrate`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `infos` | object[] | 是 | 迁移信息列表，每行一对 remote 主从 |
| `infos[].cluster_domain` | string | 是 | 集群域名 |
| `infos[].old_master_ip` | string | 是 | 旧 remote master IP |
| `infos[].old_slave_ip` | string | 是 | 旧 remote slave IP |
| `infos[].spec_id` | int | 是 | 目标规格 ID |
| `infos[].count` | int | 否（默认 `1`） | 机器组数（1组=1主+1从） |
| `infos[].labels` | string[] | 否（默认 `[]`） | 资源标签 ID 列表 |
| `backup_source` | string | 否（默认 `remote`） | 备份源 |
| `need_checksum` | bool | 否（默认 `true`） | 执行前是否数据校验 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的主从迁移单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- 支持一次传入多行，但每行的 `cluster_domain` 不能重复（同一集群一行）。
- `infos` 为空时显式报错，不产生单据。
- 按 `cluster_domain` 匹配；未找到的集群显式报错，不产生单据。
- `old_master_ip` / `old_slave_ip` 必须能反查到该集群的 remote master / slave 实例，否则显式报错。
- 目标规格按 remote（backend）类型校验（存在 + 启用）。
- `is_safe` 固定为 `true`（安全模式），不对外暴露开关。
- `ip_source` 固定为 `resource_pool`（资源池自动分配新机器）。
- **幂等防重**：在 5 分钟窗口内，同一 `creator` + `bk_biz_id` + 相同 `(cluster_id, old_master_ip, old_slave_ip)` 集合的未完结单据已存在时，直接复用该单据并返回其 `bill_id`，不会重复提单。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_tendbcluster_migrate \
  body_param='{"infos": [{"cluster_domain": "spider.test2.mysql.db", "old_master_ip": "192.168.1.12", "old_slave_ip": "192.168.1.11", "spec_id": 490}]}' \
  --raw-query "对 spider.test2.mysql.db 的 remote 主从 192.168.1.12/192.168.1.11 做主从迁移"
```

---

## `submit_bill_proxy_rebuild`：创建 TenDBHA proxy 原地重建单据

**用途**：对一批 TenDBHA 集群的 proxy 实例做原地重建，按集群分组，每个集群一行。

**operation_id**：`mysql_bill_submit_bill_proxy_rebuild`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，需同为 TenDBHA） |
| `ips` | string[] | 是 | 待重建的 proxy 实例 IP 列表 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的原地重建单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- `ips` 为空时显式报错，不产生单据。
- 每个 IP 必须能反查到 proxy 实例；未找到的 IP 显式报错，不产生单据。
- 反查所有 proxy 实例承载集群的并集必须等于输入集群，不一致时显式报错（列出缺少/多余项），防止跨集群 IP 被静默丢弃。
- 按 `cluster_id` 分组生成 `infos`，每个集群一行，`rebuild_proxy_hosts` 为该集群下的 proxy 实例列表。
- `is_safe` 固定为 `true`（安全模式），不对外暴露开关。
- **幂等防重**：在 5 分钟窗口内，同一 `creator` + `bk_biz_id` + 相同 `(cluster_id, ip 集合)` 的未完结单据已存在时，直接复用该单据并返回其 `bill_id`，不会重复提单。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_proxy_rebuild \
  body_param='{"cluster_domains": ["demo.mysql.db"], "ips": ["192.168.1.13"]}' \
  --raw-query "对 demo.mysql.db 的 proxy 实例 192.168.1.13 原地重建"
```

---

## `submit_bill_tendbha_slave_rebuild`：创建 TenDBHA 存储 slave 原地重建单据

**用途**：对一批 TenDBHA 集群的存储 slave 实例做原地重建，在原机重建实例，不申请新资源、不涉及规格选择。

**operation_id**：`mysql_bill_submit_bill_tendbha_slave_rebuild`

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domains` | string[] | 是 | 集群域名列表（支持多个，需同为 TenDBHA） |
| `ips` | string[] | 是 | 待重建的 slave 实例 IP 列表 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `bills[]` | object[] | 生成的原地重建单据列表 |
| `bills[].bill_id` | int | 单据 ID |
| `bills[].bill_url` | string | 单据链接 |

**行为约定**

- `ips` 为空时显式报错，不产生单据。
- 每个 IP 必须能反查到 slave 实例；未找到的 IP 显式报错，不产生单据。
- 反查所有 slave 实例承载集群的并集必须等于输入集群，不一致时显式报错（列出缺少/多余项），防止跨集群 IP 被静默丢弃。
- 每个 slave 实例（`ip:port`）单独一行，一行对应一个 slave 实例 + 所属集群；**原地重建不申请新资源**（无 `resource_spec` / `ip_source` 字段）。
- `backup_source` 固定为 `remote`。
- **幂等防重**：在 5 分钟窗口内，同一 `creator` + `bk_biz_id` + 相同 `(cluster_id, slave_ip, slave_port)` 的未完结单据已存在时，直接复用该单据并返回其 `bill_id`，不会重复提单。

**调用示例**

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-bill.mysql_bill_submit_bill_tendbha_slave_rebuild \
  body_param='{"cluster_domains": ["demo2.mysql.db"], "ips": ["192.168.1.14"]}' \
  --raw-query "对 demo2.mysql.db 的 slave 实例 192.168.1.14 原地重建"
```