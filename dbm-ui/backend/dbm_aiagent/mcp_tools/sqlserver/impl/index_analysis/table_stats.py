# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

P0 - get_table_stats：表上的统计对象状态

为什么 P0：
  执行计划估算偏差的根因里，"统计信息过期 / 采样不足" 占了大头。
  没有这份数据，看到 RowsRead 远高于 EstimateRows 也只能猜。

数据源：
  - sys.stats                               获取 stats_id / 统计名 / 是否自动统计 / 过滤条件
  - sys.stats_columns + sys.columns         获取统计涉及的列（按 stats_column_id 排序）
  - sys.dm_db_stats_properties              获取 last_updated / rows / rows_sampled
                                              / unfiltered_rows / modification_counter
  - sys.indexes                             用于判断这个统计是否随某个索引自动维护

设计要点：
  - is_outdated 字段在结果里直接给出（基于 modification_counter / rows 阈值），
    避免上层再实现一次"过期判定"的业界经验式规则
  - 入参 tables 支持批量；每张表独立容错（status=ok / not_found）

版本要求（重要）：
  本工具依赖 sys.dm_db_stats_properties，该 DMF 的版本下限是
  SQL Server 2008 R2 SP2 / 2012 SP1，对应：
    - 2008 RTM/SP1/SP2/SP3/SP4：不存在该 DMF，SQL 直接报
      "Cannot find the object sys.dm_db_stats_properties"
    - 2008 R2 RTM/SP1：同样不存在；需打到 2008 R2 SP2 才可用
    - 2012 RTM：不存在；需打到 2012 SP1 才可用
    - 2014 / 2016 / 2017 / 2019 / 2022：原生支持
  若目标实例为上述早期 build，请改用 sqlserver_list_table_status 的
  stats_outdated_count 字段做粗筛（它走 sys.sysindexes.rowmodctr，
  2008 RTM 起即可用，是为兼容老版本特意选择的口径）。
"""
from typing import Dict, List, Optional

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.common import DEFAULT_SCHEMA

# 经验阈值：当统计行数较小（<500）时只要修改 >= 500 就视为过期；
# 否则修改占比 >= 20% 视为过期。这是 SQL Server 内部触发自动统计更新所用阈值的近似。
_OUTDATED_ABS_THRESHOLD = 500
_OUTDATED_RATIO = 0.20


# 统计对象元信息 + 属性 一次查出来
# - 用 sys.stats 关联 sys.dm_db_stats_properties（CROSS APPLY 形式）
# - LEFT JOIN sys.indexes 判断"是否伴随某个索引"
# - has_filter / filter_definition 反映过滤统计
_STATS_META_SQL_TEMPLATE = """
SELECT
    st.stats_id                                      AS stats_id,
    st.name                                          AS stats_name,
    st.auto_created                                  AS auto_created,
    st.user_created                                  AS user_created,
    st.no_recompute                                  AS no_recompute,
    st.has_filter                                    AS has_filter,
    st.filter_definition                             AS filter_definition,
    sp.last_updated                                  AS last_updated,
    sp.rows                                          AS rows,
    sp.rows_sampled                                  AS rows_sampled,
    sp.unfiltered_rows                               AS unfiltered_rows,
    sp.modification_counter                          AS modification_counter,
    sp.steps                                         AS steps,
    -- 是否伴随索引存在（同名 sys.indexes 行存在则非纯列统计）
    CASE WHEN i.index_id IS NULL THEN 0 ELSE 1 END   AS bound_to_index,
    i.type_desc                                      AS bound_index_type
FROM sys.stats st
JOIN sys.objects o    ON o.object_id = st.object_id
JOIN sys.schemas s    ON s.schema_id = o.schema_id
LEFT JOIN sys.indexes i ON i.object_id = st.object_id AND i.index_id = st.stats_id
CROSS APPLY sys.dm_db_stats_properties(st.object_id, st.stats_id) sp
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
ORDER BY st.stats_id
""".strip()


# 统计涉及的列（按 stats_column_id 排序）
_STATS_COLUMNS_SQL_TEMPLATE = """
SELECT
    sc.stats_id                                      AS stats_id,
    sc.stats_column_id                               AS stats_column_id,
    c.name                                           AS column_name
FROM sys.stats st
JOIN sys.objects o    ON o.object_id = st.object_id
JOIN sys.schemas s    ON s.schema_id = o.schema_id
JOIN sys.stats_columns sc ON sc.object_id = st.object_id AND sc.stats_id = st.stats_id
JOIN sys.columns c    ON c.object_id = sc.object_id AND c.column_id = sc.column_id
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
ORDER BY sc.stats_id, sc.stats_column_id
""".strip()


def _judge_outdated(rows: Optional[int], modification_counter: Optional[int]) -> bool:
    """业界经验式过期判定：
    - 行数为 0/None：无法判断，按保守策略不标过期
    - 修改 < 500：不算过期
    - rows < 500：只要修改 >= 500 就算过期（小表敏感）
    - 否则：modification_counter / rows >= 20% 算过期
    """
    if not rows or modification_counter is None:
        return False
    if modification_counter < _OUTDATED_ABS_THRESHOLD:
        return False
    if rows < _OUTDATED_ABS_THRESHOLD:
        return True
    return (modification_counter / rows) >= _OUTDATED_RATIO


def _merge_stats_columns(stats: List[Dict], stats_columns: List[Dict]) -> List[Dict]:
    """把列按 stats_id 聚合到统计上，并附带 is_outdated 判定。"""
    by_id: Dict[int, Dict] = {item["stats_id"]: item for item in stats}
    for item in stats:
        item["columns"] = []
        item["is_outdated"] = _judge_outdated(item.get("rows"), item.get("modification_counter"))

    for col in stats_columns:
        item = by_id.get(col["stats_id"])
        if not item:
            continue
        item["columns"].append(col["column_name"])
    return stats


def _query_one_table_stats(
    bk_cloud_id: int,
    address: str,
    quoted_db: str,
    schema: str,
    table: str,
) -> List[Dict]:
    """单表查询统计对象。空表抛 DBMMcpBaseException 由外层转 not_found。"""
    meta_sql = _STATS_META_SQL_TEMPLATE.format(schema=schema, table=table)
    stats = run_user_db_read(bk_cloud_id, address, quoted_db, meta_sql, "get_table_stats(meta)")
    if not stats:
        raise DBMMcpBaseException(msg=f"no stats found, table may not exist: [{schema}].[{table}]")

    columns_sql = _STATS_COLUMNS_SQL_TEMPLATE.format(schema=schema, table=table)
    stats_columns = run_user_db_read(bk_cloud_id, address, quoted_db, columns_sql, "get_table_stats(columns)")
    return _merge_stats_columns(stats, stats_columns)


def sqlserver_get_table_stats(
    cluster_domain: str,
    dbname: str,
    tables: List[str],
    schema: str = DEFAULT_SCHEMA,
    address: Optional[str] = None,
) -> Dict:
    """批量获取表统计对象清单及更新状态。

    版本要求：SQL Server 2008 R2 SP2 / 2012 SP1 及以上（依赖 sys.dm_db_stats_properties）。
    若实例为更早的 2008 RTM/SP1/SP2/SP3/SP4 或 2008 R2 RTM/SP1 / 2012 RTM，
    SQL 会报 "Cannot find the object sys.dm_db_stats_properties"，
    此时请改用 sqlserver_list_table_status 的 stats_outdated_count 字段做粗筛。

    is_outdated 判定规则（业界经验式，近似 SQL Server 自动更新统计阈值）：
      - rows 为 0/None 或 modification_counter 为 None：不标过期
      - modification_counter < 500：不标过期
      - rows < 500 且 modification_counter >= 500：标过期（小表敏感）
      - 否则 modification_counter / rows >= 20%：标过期

    :param cluster_domain: 目标集群域名
    :param dbname: 目标用户库名
    :param tables: 目标表名列表（1~20，整批共用 schema；重复项保序去重）
    :param schema: schema 名，默认 dbo
    :param address: 可选；指定具体实例地址，否则按集群默认路由（一般落到从库只读账号）
    :return: {
        "cluster_domain", "address", "role", "dbname", "schema",
        "table_count", "ok_count",
        "results": [
            {
                "table", "status",        # status: ok / not_found
                "error",                  # 仅 not_found 时非空
                "stats": [                # 该表全部统计对象
                    {
                        "stats_id", "stats_name",
                        "auto_created", "user_created", "no_recompute",
                        "has_filter", "filter_definition",
                        "last_updated", "rows", "rows_sampled",
                        "unfiltered_rows", "modification_counter", "steps",
                        "bound_to_index", "bound_index_type",
                        "columns": [...],       # 参与统计的列名（按 stats_column_id 排序）
                        "is_outdated": bool,    # 见上面判定规则
                    }, ...
                ],
                "stats_count": N,
                "outdated_count": M,            # is_outdated 为 True 的统计对象数
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
    for tbl in unique_tables:
        quote_sqlserver_ident(tbl)
        try:
            stats = _query_one_table_stats(bk_cloud_id, target["address"], quoted_db, schema, tbl)
            outdated_count = sum(1 for s in stats if s.get("is_outdated"))
            results.append(
                {
                    "table": tbl,
                    "status": "ok",
                    "error": None,
                    "stats": stats,
                    "stats_count": len(stats),
                    "outdated_count": outdated_count,
                }
            )
            ok_count += 1
        except DBMMcpBaseException as exc:
            results.append(
                {
                    "table": tbl,
                    "status": "not_found",
                    "error": str(exc),
                    "stats": [],
                    "stats_count": 0,
                    "outdated_count": 0,
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
