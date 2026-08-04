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

> operation_id 完整形式：`mysql_bill_` + 上表方法名，如 `mysql_bill_submit_bill_mysql_disable`。

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
