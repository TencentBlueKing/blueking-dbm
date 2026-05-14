# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

P0 - get_table_indexes：表上现有索引

输出每个索引的：
  - 类型（CLUSTERED / NONCLUSTERED / 列存储）、唯一性、是否禁用、是否填充因子
  - key_columns（按 key_ordinal 排序、含升降序）
  - included_columns（INCLUDE 列）
  - has_filter / filter_definition（过滤索引）
  - 行数（粗略，从 sys.partitions.rows 取 heap/聚簇主分区）
  - 数据/索引压缩状态

是否需要 dm_db_index_usage_stats / dm_db_index_physical_stats 这种"运行画像"放到独立工具里。
本工具只回答"表上有哪些索引"。

入参 tables 支持批量；每张表独立容错（status=ok / not_found）。
"""
from typing import Dict, List, Optional

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.common import DEFAULT_SCHEMA

# 索引基本信息：一行一个索引
_INDEX_META_SQL_TEMPLATE = """
SELECT
    i.index_id                                       AS index_id,
    i.name                                           AS index_name,
    i.type                                           AS type_id,
    i.type_desc                                      AS type_desc,
    i.is_unique                                      AS is_unique,
    i.is_primary_key                                 AS is_primary_key,
    i.is_unique_constraint                           AS is_unique_constraint,
    i.is_disabled                                    AS is_disabled,
    i.has_filter                                     AS has_filter,
    i.filter_definition                              AS filter_definition,
    i.fill_factor                                    AS fill_factor,
    i.is_padded                                      AS is_padded,
    -- 行数与压缩状态：取该索引第一个分区的代表值
    -- partition_number = 1 适用于绝大多数非分区表场景；分区表这里只反映主分区，
    --   分析时若要严谨可结合 sys.partitions 进一步查
    ISNULL(p.rows, 0)                                AS approx_rows,
    p.data_compression_desc                          AS data_compression
FROM sys.indexes i
JOIN sys.objects o       ON o.object_id = i.object_id
JOIN sys.schemas s       ON s.schema_id = o.schema_id
LEFT JOIN sys.partitions p ON p.object_id = i.object_id
                          AND p.index_id  = i.index_id
                          AND p.partition_number = 1
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
  AND i.type IN (0, 1, 2, 5, 6)   -- HEAP/CLUSTERED/NONCLUSTERED/CLUSTERED COLUMNSTORE/NONCLUSTERED COLUMNSTORE
ORDER BY i.index_id
""".strip()


# 索引列信息：key 列与 INCLUDE 列各一行；用 is_included_column 区分
_INDEX_COLUMNS_SQL_TEMPLATE = """
SELECT
    i.index_id                                       AS index_id,
    ic.key_ordinal                                   AS key_ordinal,
    ic.index_column_id                               AS index_column_id,
    ic.is_included_column                            AS is_included_column,
    ic.is_descending_key                             AS is_descending,
    c.name                                           AS column_name
FROM sys.indexes i
JOIN sys.objects o       ON o.object_id = i.object_id
JOIN sys.schemas s       ON s.schema_id = o.schema_id
JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
JOIN sys.columns c        ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
  AND i.type IN (0, 1, 2, 5, 6)
ORDER BY i.index_id, ic.is_included_column, ic.key_ordinal, ic.index_column_id
""".strip()


def _merge_columns_into_indexes(indexes: List[Dict], index_columns: List[Dict]) -> List[Dict]:
    """把列行按 index_id 聚合进每个索引：key_columns / included_columns。"""
    by_id: Dict[int, Dict] = {idx["index_id"]: idx for idx in indexes}
    for idx in indexes:
        idx["key_columns"] = []
        idx["included_columns"] = []

    for col in index_columns:
        idx = by_id.get(col["index_id"])
        if not idx:
            continue
        if col.get("is_included_column"):
            idx["included_columns"].append(
                {
                    "name": col["column_name"],
                }
            )
        else:
            idx["key_columns"].append(
                {
                    "name": col["column_name"],
                    "ordinal": col["key_ordinal"],
                    "is_descending": bool(col["is_descending"]),
                }
            )
    return indexes


def _query_one_table_indexes(
    bk_cloud_id: int,
    address: str,
    quoted_db: str,
    schema: str,
    table: str,
) -> List[Dict]:
    """单表查询索引清单。空表抛 DBMMcpBaseException 由外层转为 not_found。"""
    meta_sql = _INDEX_META_SQL_TEMPLATE.format(schema=schema, table=table)
    indexes = run_user_db_read(bk_cloud_id, address, quoted_db, meta_sql, "get_table_indexes(meta)")
    if not indexes:
        raise DBMMcpBaseException(msg=f"table not found or has no indexes: [{schema}].[{table}]")

    columns_sql = _INDEX_COLUMNS_SQL_TEMPLATE.format(schema=schema, table=table)
    index_columns = run_user_db_read(bk_cloud_id, address, quoted_db, columns_sql, "get_table_indexes(columns)")
    return _merge_columns_into_indexes(indexes, index_columns)


def sqlserver_get_table_indexes(
    cluster_domain: str,
    dbname: str,
    tables: List[str],
    schema: str = DEFAULT_SCHEMA,
    address: Optional[str] = None,
) -> Dict:
    """批量获取目标表上现有索引清单（含 key 列、INCLUDE 列、唯一性、近似行数等）。

    数据源：sys.indexes / sys.index_columns / sys.columns / sys.partitions
    使用通道：sqlserver_data_read_rpc（业务库只读账号）

    :param cluster_domain: 集群不可变域名
    :param dbname: 目标数据库名（白名单校验）
    :param tables: 目标表名列表（1~20 个，整批共用同一 schema；列表内重复项会被去重并保持首次出现的顺序）
    :param schema: 表所在 schema，默认 dbo
    :param address: 可选实例地址；不传时缺省走 master
    :return: {
        "cluster_domain", "address", "role", "dbname", "schema",
        "table_count", "ok_count",
        "results": [
            {"table", "status", "error",
             "indexes": [...], "index_count": N},
            ...
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
    for tbl in unique_tables:
        quote_sqlserver_ident(tbl)
        try:
            indexes = _query_one_table_indexes(bk_cloud_id, target["address"], quoted_db, schema, tbl)
            results.append(
                {
                    "table": tbl,
                    "status": "ok",
                    "error": None,
                    "indexes": indexes,
                    "index_count": len(indexes),
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
        "table_count": len(unique_tables),
        "ok_count": ok_count,
        "results": results,
    }
