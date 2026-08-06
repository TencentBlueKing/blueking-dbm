# explain_sql

MySQL EXPLAIN MCP 实现。对外入口：`explain_sql()`（`__init__.py`）。

## 目录结构

```
explain_sql/
├── __init__.py      # 入口：sanitize → 按 cluster_type 分叉
├── drs.py           # run_explain()：DRS 下发 USE + EXPLAIN
├── single_ha.py     # TenDBSingle / TenDBHA
├── tendbcluster.py  # TenDBCluster 分片路由
└── README.md
```

## 调用链

```
mysql_query_mcp.explain_sql
  └── explain_sql(cluster_type, cluster_domain, dbname, query_sql)
        ├── sanitize_select_sql          # 公共 step 1
        ├── TenDBCluster → explain_tendbcluster   # step 2–7
        └── Single/HA    → explain_single_ha
```

## 公共 step 1：sanitize_select_sql

- 安全校验（黑名单、AST 白名单、危险函数等）
- UPDATE / DELETE / INSERT...SELECT → 等价 SELECT（只读账号可 EXPLAIN）
- **不改库名**（`rewrite_spider_dbname=False`）

## TenDBSingle / TenDBHA

1. `get_cloud_slave_address_and_dbname` 找 slave 地址（及 USE 库名）
2. `run_explain` 下发 EXPLAIN

## TenDBCluster（step 2–7）

| Step | 函数 | 说明 |
|------|------|------|
| 2 | `_parse_route_context` | 解析库表、JOIN、WHERE/ON 等值条件 |
| 3 | `_fetch_spider_table_creates` | Spider 上 SHOW CREATE TABLE，解析 shard 元数据 |
| 4 | `_match_shard_key_values` | 从 WHERE/JOIN ON 匹配 shard_key 字面量（`=` / `IN`） |
| 5 | `_apply_shard_ids` | 有值：`crc32(value) % N`；无值：默认 `0` |
| 6 | `_rewrite_sql_for_shard` | 逻辑库名 → `db_{shard_id}`（系统库跳过） |
| 7 | `_explain_on_remote_slave` | 连对应分片 remote slave 执行 EXPLAIN |

**shard_id 选取**：FROM 第一张驱动表的 shard_id。

**shard_key 解析**（优先级）：

1. 表 COMMENT：`shard_key "col"`
2. 兜底：从 `PARTITION BY LIST (crc32(\`col\`) MOD N)` 提取 `col`

**shard_key 匹配策略**：

- 只处理 `=` 和 `IN (字面量)`
- JOIN 等值传递（`a.id = b.id` 且已知 `a.id = 1`）
- `IN (1,2,3)` 只取第一个值；无法确定分片 → shard_id = 0

## MCP 返回

```python
{
    "explain_result": [...],  # DRS EXPLAIN 结果
    "rewritten": bool,        # 仅表示 step 1 是否 DML→SELECT
}
```

### `rewritten` 含义

| 场景 | `rewritten` |
|------|-------------|
| 用户提交 SELECT | `False` |
| 用户提交 UPDATE/DELETE/INSERT...SELECT | `True` |

TenDBCluster 的库名改写（`dbtest` → `dbtest_2`）是内部分片路由，**不计入** `rewritten`。

## 日志

关键节点打 INFO（不打印完整 SQL，只打 `sql_len`）：

- 入口：cluster、type、db、rewritten
- tendbcluster：表数、shard_id、physical_db、address
- drs：address、use_db、sql_len

## 测试

```bash
source bin/environ.sh
export DJANGO_SETTINGS_MODULE=config.ci
.venv/bin/pytest backend/tests/dbm_aiagent/mcp_tools/mysql/impl/test_explain_sql_tendbcluster.py -v
```
