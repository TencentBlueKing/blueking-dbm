# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

P1 - get_index_usage_stats：索引使用画像

数据源（主从关系很重要）：
  - sys.indexes                       —— 主表，确保"创建后从未被任何查询触达"的索引也被列出
  - sys.dm_db_index_usage_stats       —— LEFT JOIN 进来；该 DMV 是"实例启动以来累计值"，重启清空
  - sys.dm_exec_sessions              —— 取 session_id<=4 的最早 login_time 近似 sqlserver_start_time
                                          （这里特意没用 sys.dm_os_sys_info.sqlserver_start_time，
                                            因为该字段在 SQL Server 2008 不存在）

注意点：
  - 0 个 user_seek/scan/lookup 的索引并不一定无用：可能这段时间没业务命中
  - user_updates 高 + user_seek/scan/lookup 都为 0 → 强烈嫌疑冗余索引
  - HEAP（i.type=0）不计；列存储（i.type=5/6）虽有 user_seeks 但语义不同，本工具仍纳入
  - 业务库只读账号通道（sqlserver_data_read_rpc），默认走从库

入参 tables 支持批量；每张表独立容错（status=ok / not_found）。
sqlserver_start_time 是全实例属性，在结果顶层返回一次（行内不重复携带）。
"""
from typing import Dict, List, Optional

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.common import DEFAULT_SCHEMA

# 一行一索引；同时取 sqlserver_start_time 作为参考列（每行都带，便于 LLM 直接看到）
_INDEX_USAGE_SQL_TEMPLATE = """
SELECT
    i.index_id                                       AS index_id,
    i.name                                           AS index_name,
    i.type_desc                                      AS type_desc,
    i.is_unique                                      AS is_unique,
    i.is_primary_key                                 AS is_primary_key,
    ISNULL(us.user_seeks, 0)                         AS user_seeks,
    ISNULL(us.user_scans, 0)                         AS user_scans,
    ISNULL(us.user_lookups, 0)                       AS user_lookups,
    ISNULL(us.user_updates, 0)                       AS user_updates,
    us.last_user_seek                                AS last_user_seek,
    us.last_user_scan                                AS last_user_scan,
    us.last_user_lookup                              AS last_user_lookup,
    us.last_user_update                              AS last_user_update,
    -- 实例启动时间：用 sys.dm_exec_sessions(session_id <= 4) 的最早 login_time 近似
    --   原因：sys.dm_os_sys_info.sqlserver_start_time 在 SQL Server 2008 不存在，
    --   而本字段 2008+ 都稳定可用，与 instance_summary 工具的口径保持一致
    (SELECT MIN(login_time) FROM sys.dm_exec_sessions WHERE session_id <= 4) AS sqlserver_start_time
FROM sys.indexes i
JOIN sys.objects o    ON o.object_id = i.object_id
JOIN sys.schemas s    ON s.schema_id = o.schema_id
LEFT JOIN sys.dm_db_index_usage_stats us
       ON us.object_id = i.object_id
      AND us.index_id  = i.index_id
      AND us.database_id = DB_ID()
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
  AND i.type IN (1, 2, 5, 6)   -- 排除 HEAP（type=0），HEAP 没有索引意义
ORDER BY i.index_id
""".strip()


def sqlserver_get_index_usage_stats(
    cluster_domain: str,
    dbname: str,
    tables: List[str],
    schema: str = DEFAULT_SCHEMA,
    address: Optional[str] = None,
) -> Dict:
    """批量获取目标表上每个索引的使用画像（seek/scan/lookup/update 累计计数）。

    数据源：sys.indexes LEFT JOIN sys.dm_db_index_usage_stats
            （已过滤 HEAP，仅返回 type IN (1,2,5,6)：聚集/非聚集/列存储 等真实索引）
    通道：  sqlserver_data_read_rpc（业务库只读账号，默认落从库）

    累计计数说明：
      sys.dm_db_index_usage_stats 的 user_seeks/scans/lookups/updates 是
      "实例启动以来的累计值"，SQL Server 服务重启会清空。返回结果顶层
      sqlserver_start_time 即累计基准起点；若该字段距今很近，说明计数样本不足，
      不能据此判断"索引无用"。

    :param cluster_domain: 目标集群域名
    :param dbname: 目标用户库名
    :param tables: 目标表名列表（1~20，整批共用 schema；重复项保序去重）
    :param schema: schema 名，默认 dbo
    :param address: 可选；指定具体实例地址，否则按集群默认路由
    :return: {
        "cluster_domain", "address", "role", "dbname", "schema",
        "sqlserver_start_time": "...",   # 累计计数的"基准起点"，全实例一份
        "table_count", "ok_count",
        "results": [
            {
                "table", "status", "error",
                "indexes": [
                    {
                        "index_id", "index_name", "type_desc",
                        "is_unique", "is_primary_key",
                        "user_seeks", "user_scans", "user_lookups", "user_updates",
                        "last_user_seek", "last_user_scan",
                        "last_user_lookup", "last_user_update",
                    }, ...
                ],
                "index_count": N,
            }, ...
        ],
    }
    """
    # 去重并保持顺序：dict.fromkeys 在 Python 3.7+ 保证插入顺序，等价于"保序去重"
    unique_tables = list(dict.fromkeys(tables))
    # dbname / schema 是循环不变量，只在循环外校验一次；表名在循环里逐个校验
    quoted_db = quote_sqlserver_ident(dbname)
    quote_sqlserver_ident(schema)
    bk_cloud_id, target = resolve_target_instance(cluster_domain, address)

    results: List[Dict] = []
    ok_count = 0
    sqlserver_start_time: Optional[str] = None

    for tbl in unique_tables:
        quote_sqlserver_ident(tbl)
        sql = _INDEX_USAGE_SQL_TEMPLATE.format(schema=schema, table=tbl)
        try:
            rows = run_user_db_read(bk_cloud_id, target["address"], quoted_db, sql, "get_index_usage_stats")
            if not rows:
                raise DBMMcpBaseException(msg=f"table not found or has no non-heap indexes: [{schema}].[{tbl}]")
            # 启动时间提到顶层（每行都一样），瘦身行内容；只在第一次成功时记录
            if sqlserver_start_time is None:
                sqlserver_start_time = rows[0].get("sqlserver_start_time")
            for r in rows:
                r.pop("sqlserver_start_time", None)

            results.append(
                {
                    "table": tbl,
                    "status": "ok",
                    "error": None,
                    "indexes": rows,
                    "index_count": len(rows),
                }
            )
            ok_count += 1
        except DBMMcpBaseException as exc:
            results.append(
                {
                    "table": tbl,
                    "status": "not_found",
                    "error": str(exc),
                    "indexes": [],
                    "index_count": 0,
                }
            )

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "dbname": dbname,
        "schema": schema,
        "sqlserver_start_time": sqlserver_start_time,
        "table_count": len(unique_tables),
        "ok_count": ok_count,
        "results": results,
    }
