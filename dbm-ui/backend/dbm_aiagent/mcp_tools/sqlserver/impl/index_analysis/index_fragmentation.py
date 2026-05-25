# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

P1 - get_index_fragmentation：索引碎片率

数据源：sys.dm_db_index_physical_stats(LIMITED 模式)
为何固定 LIMITED：
  - LIMITED 只读叶层级以上的页，对 IO/锁的影响最小，分析场景的标配
  - SAMPLED / DETAILED 会做更深扫描，可能拖垮线上库，不适合自动化工具默认行为

仅返回 i.type IN (1,2)，即聚集/非聚集 B-Tree 索引；明确排除：
  - HEAP（type=0）：无"索引碎片"概念，谈论的是堆的转发记录/未使用页
  - 列存储（type=5/6）：碎片度量逻辑完全不同（segment 健康度而非页连续性）

输出包含 page_count，便于 LLM 自行判断"是否值得 REORG/REBUILD"
（业界经验：page_count < 1000 的小索引通常不必处理碎片，因此 min_page_count 默认 1000）。

入参 tables 支持批量；每张表独立容错（status=ok / not_found）。
"""
from typing import Dict, List, Optional

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.common import DEFAULT_SCHEMA

# 用 OBJECT_ID('schema.table') 把表名定位为 object_id 后传入 dm_db_index_physical_stats
# - DB_ID()                        当前库（已 USE [dbname]）
# - OBJECT_ID(N'[schema].[table]')  当前库下 schema.table 的 object_id
# - NULL, NULL                     全部索引、全部分区
# - 'LIMITED'                      限定扫描深度（叶层之上），最快、最省资源
_INDEX_FRAG_SQL_TEMPLATE = """
SELECT
    ips.index_id                                     AS index_id,
    i.name                                           AS index_name,
    ips.index_type_desc                              AS index_type_desc,
    ips.alloc_unit_type_desc                         AS alloc_unit_type,
    ips.partition_number                             AS partition_number,
    ips.avg_fragmentation_in_percent                 AS avg_fragmentation_pct,
    ips.fragment_count                               AS fragment_count,
    ips.avg_fragment_size_in_pages                   AS avg_fragment_size_pages,
    ips.page_count                                   AS page_count,
    ips.record_count                                 AS record_count
FROM sys.dm_db_index_physical_stats(
        DB_ID(),
        OBJECT_ID(N'[{schema}].[{table}]'),
        NULL, NULL, 'LIMITED'
     ) ips
JOIN sys.indexes i
       ON i.object_id = ips.object_id
      AND i.index_id  = ips.index_id
WHERE i.type IN (1, 2)   -- CLUSTERED / NONCLUSTERED；列存储和 HEAP 不在本工具范畴
ORDER BY ips.index_id, ips.partition_number
""".strip()


def sqlserver_get_index_fragmentation(
    cluster_domain: str,
    dbname: str,
    tables: List[str],
    schema: str = DEFAULT_SCHEMA,
    address: Optional[str] = None,
    min_page_count: int = 1000,
) -> Dict:
    """批量获取目标表上各索引的碎片状态（LIMITED 模式扫描，对线上影响最小）。

    数据源：sys.dm_db_index_physical_stats(DB_ID(), OBJECT_ID(...), NULL, NULL, 'LIMITED')
            JOIN sys.indexes，仅返回 i.type IN (1,2)（聚集/非聚集 B-Tree 索引）。

    :param cluster_domain: 目标集群域名
    :param dbname: 目标用户库名
    :param tables: 目标表名列表（1~20，整批共用 schema；重复项保序去重）
    :param schema: schema 名，默认 dbo
    :param address: 可选；指定具体实例地址，否则按集群默认路由
    :param min_page_count: 仅返回 page_count >= 该阈值的索引行，默认 1000；传 0 表示不过滤。
                           默认 1000 的依据：page_count < 1000 的小索引（约 < 8MB）即便
                           碎片率高，REORG/REBUILD 收益也极小，过滤掉可降低 LLM 噪音。
                           注意：过滤是"行级"的；若某表所有索引都被过滤，该表 status 仍为 ok，
                           只是 indexes 为空、row_count=0。

    :raises DBMMcpBaseException: min_page_count < 0 时抛出

    :return: {
        "cluster_domain", "address", "role", "dbname", "schema",
        "scan_mode": "LIMITED",
        "min_page_count": <实际生效的过滤阈值>,
        "table_count", "ok_count",
        "results": [
            {
                "table", "status", "error",   # status: ok / not_found
                "indexes": [
                    {
                        "index_id", "index_name",
                        "index_type_desc", "alloc_unit_type",
                        "partition_number",
                        "avg_fragmentation_pct",      # 0~100，建议 5~30 REORG，>30 REBUILD
                        "fragment_count",
                        "avg_fragment_size_pages",
                        "page_count",                 # 索引占用页数，min_page_count 过滤即按此字段
                        "record_count",
                    }, ...
                ],
                "row_count": N,                   # 过滤后实际返回行数
            }, ...
        ],
    }
    """
    if min_page_count < 0:
        raise DBMMcpBaseException(msg="min_page_count must be >= 0")

    # 去重并保持顺序：dict.fromkeys 在 Python 3.7+ 保证插入顺序，等价于"保序去重"
    unique_tables = list(dict.fromkeys(tables))
    # dbname / schema 是循环不变量，只在循环外校验一次；表名在循环里逐个校验
    quoted_db = quote_sqlserver_ident(dbname)
    quote_sqlserver_ident(schema)
    bk_cloud_id, target = resolve_target_instance(cluster_domain, address)

    results: List[Dict] = []
    ok_count = 0
    for tbl in unique_tables:
        quote_sqlserver_ident(tbl)
        sql = _INDEX_FRAG_SQL_TEMPLATE.format(schema=schema, table=tbl)
        try:
            rows = run_user_db_read(bk_cloud_id, target["address"], quoted_db, sql, "get_index_fragmentation")
            # 表存在但全部索引都被过滤是合法情况；只有完全空才视作表不存在
            if not rows:
                raise DBMMcpBaseException(msg=f"no rowstore index found, table may not exist: [{schema}].[{tbl}]")
            if min_page_count > 0:
                rows = [r for r in rows if (r.get("page_count") or 0) >= min_page_count]

            results.append(
                {
                    "table": tbl,
                    "status": "ok",
                    "error": None,
                    "indexes": rows,
                    "row_count": len(rows),
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
                    "row_count": 0,
                }
            )

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "dbname": dbname,
        "schema": schema,
        "scan_mode": "LIMITED",
        "min_page_count": min_page_count,
        "table_count": len(unique_tables),
        "ok_count": ok_count,
        "results": results,
    }
