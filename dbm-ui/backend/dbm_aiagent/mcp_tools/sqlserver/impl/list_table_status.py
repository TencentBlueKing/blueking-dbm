# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

list_table_status：列出业务库下用户表的状态信息（行数/大小/统计新鲜度等）

定位：
    "表清单/前置定位"工具，与 list_databases 同层，独立于索引分析功能域。
    上游分析工具（get_table_schema / get_table_indexes / get_table_stats /
    get_index_usage_stats / get_index_fragmentation 等）需要先知道
    "该库里有哪些值得分析的表"，本工具承担前置定位作用：一次性汇总每张表的
    体量、最近写入活跃度与统计过期度，方便上层挑出"数据量大且统计过期"的
    表作为优化重点。

输出字段（detail 模式，全版本统一）：
    - schema_name / table_name / object_id
    - 物理体量：row_count / total_size_mb / data_size_mb / index_size_mb
    - 结构特征：is_heap / index_count / partition_count / has_primary_key
    - 时间维度：create_date / modify_date（最近一次 DDL）
    - 使用画像：last_user_seek / last_user_scan / last_user_lookup / last_user_update
    - 统计活性：total_modification_counter / stats_outdated_count

输出粒度控制 verbose（三态枚举，互斥）：
    - verbose="summary"（默认）：只返回 schema_name / table_name / row_count / total_size_mb，
                                 4 个字段足以快速浏览全库表清单，token 量约为 detail 的 15-20%；
                                 解决小上下文模型 token 撑爆问题
    - verbose="detail"          ：返回上面列出的全部 20 个字段，用于索引分析等深度场景
    - verbose="count_only"      ：跳过大 SQL，只跑一条 COUNT(*)，返回 total_user_table_count；
                                 tables 为空数组、limit 置 0；用于回答
                                 "这个库（或 schema）一共有多少张用户表"，
                                 解决"limit 截断后不知道库里到底有多少表"的问题；
                                 仍然支持 schema / table_name 过滤；
                                 此模式下排序参数（order_by / order）静默忽略

排序控制（order_by + order，互斥白名单）：
    - order_by：排序键，从下方 ALLOWED_ORDER_BY 中选择，缺省为 total_size_mb
        * total_size_mb        ：找大表（最常见入口）
        * row_count            ：找行数最多 / 最少的表
        * index_size_mb        ：找索引膨胀的表
        * stats_outdated_count ：找统计过期最严重的表（UPDATE STATISTICS 候选）
        * last_user_update     ：按写入活跃度排序，desc=最近被写，asc=最久未被写
    - order  ：排序方向，"desc"（默认）或 "asc"，非法值容错回落到 desc
    - 主排序键并列时，统一用 o.name ASC 作为稳定 tie-breaker
    - 注意：summary 模式只返回 4 个 L1 字段；若按非 L1 字段排序，明细里看不到该字段值，
            如需查看请用 verbose=detail

跨版本兼容（SQL Server 2008 → 2022）：
    - 主查询用 TOP (@p_limit) 而非 OFFSET/FETCH（OFFSET 是 2012+）
    - 统计过期度统一走 sys.sysindexes（2008 RTM 起即可用），
      具体 SQL 在 helpers.sqlserver_stats.build_stats_outdated_sql() 中集中维护
    - 其他对象（sys.objects / sys.schemas / sys.indexes / sys.partitions /
      sys.dm_db_partition_stats / sys.dm_db_index_usage_stats / sys.key_constraints）
      在 2008 RTM 起字段稳定

通道：
    sqlserver_data_read_rpc（业务库只读 + 已授予 VIEW SERVER STATE）。
"""
from typing import Dict, List, Optional

from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident, quote_table_idents
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sqlserver_stats import build_stats_outdated_sql

# 默认返回数量上限：避免实例上数千张表时一次返回过大
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

# verbose 输出粒度（三态枚举，互斥）：
#   - summary    ：默认，仅 4 个 L1 字段，token 友好
#   - detail     ：全部 20 个字段，索引分析等深度场景
#   - count_only ：跳过大 SQL，只跑一条 COUNT(*)，仅返回总数；排序参数被忽略
VERBOSE_SUMMARY = "summary"
VERBOSE_DETAIL = "detail"
VERBOSE_COUNT_ONLY = "count_only"
ALLOWED_VERBOSE = (VERBOSE_SUMMARY, VERBOSE_DETAIL, VERBOSE_COUNT_ONLY)

# summary 模式下保留的字段（L1 核心字段，足以浏览"哪些表大"）
# 砍掉 6 个时间戳 + object_id + 结构特征 + 统计活性，token 量约为 detail 的 15-20%
SUMMARY_FIELDS = ("schema_name", "table_name", "row_count", "total_size_mb")

# 排序白名单：逻辑字段名 -> 主查询中真实可排序的 SQL 表达式
#   - 严格白名单，绝不允许外部字符串拼到 SQL 里（防注入）
#   - 表达式与主查询 SELECT 子句中的来源保持一致：
#       * 大小类：用底层派生表的原始页数列（避免 / 1024 截断后 ORDER 时的精度损失）
#       * 时间类：使用画像列允许 NULL，对 NULL 的排序行为由 SQL Server 默认处理
#         （ASC：NULL 在前；DESC：NULL 在后），符合"最久未写入 / 最近被写入"的语义
#       * 统计类：取自 soc 派生表，已 ISNULL 过
#   - 仅暴露 5 个核心键（覆盖 90% 场景），减小 LLM 决策面与误用概率：
#       * total_size_mb        ：找大表（最常见入口）
#       * row_count            ：找行数最多 / 最少的表
#       * index_size_mb        ：找索引膨胀的表
#       * stats_outdated_count ：找统计过期最严重的表（UPDATE STATISTICS 候选）
#       * last_user_update     ：按写入活跃度排序，desc=最近被写，asc=最久未被写
ALLOWED_ORDER_BY: Dict[str, str] = {
    "total_size_mb": "ISNULL(ps.reserved_pages, 0)",
    "row_count": "ISNULL(ps.row_count, 0)",
    "index_size_mb": "ISNULL(ps.index_pages, 0)",
    "stats_outdated_count": "ISNULL(soc.stats_outdated_count, 0)",
    "last_user_update": "us.last_user_update",
}
DEFAULT_ORDER_BY = "total_size_mb"

# 排序方向白名单
ORDER_DESC = "desc"
ORDER_ASC = "asc"
ALLOWED_ORDER = (ORDER_DESC, ORDER_ASC)
DEFAULT_ORDER = ORDER_DESC

# count_only 专用：仅统计当前库下用户表总数，不查任何明细
# 复用现有 schema_filter / table_filter 拼接逻辑，过滤粒度与主查询保持一致
_LIST_TABLE_STATUS_COUNT_SQL_TEMPLATE = """
SELECT COUNT(*) AS total_user_table_count
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id = o.schema_id
WHERE o.type = 'U'
  AND o.is_ms_shipped = 0
  {schema_filter}
  {table_filter}
""".strip()

# 主查询：每个用户表一行，按可配置 ORDER BY 排序
#
# 关键点：
#   - 用 sys.dm_db_partition_stats 聚合得到行数 / 数据页 / 索引页 / LOB 页
#     在 2008 RTM 即可用，且 lob_used_page_count 列已存在
#   - 主键存在性来自 sys.key_constraints（2008 RTM 即可用）
#   - 索引/分区数来自 sys.indexes / sys.partitions
#   - 使用画像取所有索引上的最大值（任一索引被访问过即视为表被访问过）
#   - LEFT JOIN stats_outdated 派生表：统计过期度（跨版本统一走 sys.sysindexes）
#
# 注意：
#   原本 7 个聚合块用 WITH 形式（CTE）拼接，但执行通道不允许 WITH 起首的语句，
#   故改写为"SELECT 起首 + FROM 子句中的派生表（derived table）"形式。
#   各聚合块在主查询中均只被引用一次、无自引用/递归，因此与 CTE 完全语义等价，
#   优化器对两种形式生成的执行计划在大多数情况下是一致的。
_LIST_TABLE_STATUS_SQL_TEMPLATE = """
SELECT TOP ({limit})
    s.name                                              AS schema_name,
    o.name                                              AS table_name,
    o.object_id                                         AS object_id,
    o.create_date                                       AS create_date,
    o.modify_date                                       AS modify_date,
    ISNULL(ix.is_heap, 0)                               AS is_heap,
    ISNULL(ix.index_count, 0)                           AS index_count,
    ISNULL(pc.partition_count, 1)                       AS partition_count,
    CASE WHEN pk.object_id IS NULL THEN 0 ELSE 1 END    AS has_primary_key,
    ISNULL(ps.row_count, 0)                             AS row_count,
    -- 1 page = 8 KB；统一折算为 MB 便于阅读
    ISNULL(ps.reserved_pages, 0) * 8 / 1024             AS total_size_mb,
    ISNULL(ps.data_pages, 0)     * 8 / 1024             AS data_size_mb,
    ISNULL(ps.index_pages, 0)    * 8 / 1024             AS index_size_mb,
    us.last_user_seek                                   AS last_user_seek,
    us.last_user_scan                                   AS last_user_scan,
    us.last_user_lookup                                 AS last_user_lookup,
    us.last_user_update                                 AS last_user_update,
    ISNULL(soc.total_modification_counter, 0)           AS total_modification_counter,
    ISNULL(soc.stats_outdated_count, 0)                 AS stats_outdated_count
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id = o.schema_id
LEFT JOIN (
    SELECT
        ps.object_id,
        SUM(CASE WHEN ps.index_id IN (0, 1) THEN ps.row_count ELSE 0 END)        AS row_count,
        SUM(ps.reserved_page_count)                                              AS reserved_pages,
        SUM(ps.used_page_count)                                                  AS used_pages,
        SUM(
            CASE
                WHEN ps.index_id < 2
                    THEN ps.in_row_data_page_count + ps.lob_used_page_count + ps.row_overflow_used_page_count
                ELSE ps.lob_used_page_count + ps.row_overflow_used_page_count
            END
        )                                                                        AS data_pages,
        SUM(
            CASE WHEN ps.index_id < 2
                THEN ps.used_page_count
                    - (ps.in_row_data_page_count + ps.lob_used_page_count + ps.row_overflow_used_page_count)
                ELSE ps.used_page_count
                    - (ps.lob_used_page_count + ps.row_overflow_used_page_count)
            END
        )                                                                        AS index_pages
    FROM sys.dm_db_partition_stats ps
    GROUP BY ps.object_id
) ps ON ps.object_id = o.object_id
LEFT JOIN (
    SELECT
        i.object_id,
        SUM(CASE WHEN i.index_id BETWEEN 1 AND 254 THEN 1 ELSE 0 END)            AS index_count,
        MAX(CASE WHEN i.index_id = 0 THEN 1 ELSE 0 END)                          AS is_heap
    FROM sys.indexes i
    GROUP BY i.object_id
) ix ON ix.object_id = o.object_id
LEFT JOIN (
    SELECT
        p.object_id,
        COUNT(DISTINCT p.partition_number)                                       AS partition_count
    FROM sys.partitions p
    WHERE p.index_id IN (0, 1)
    GROUP BY p.object_id
) pc ON pc.object_id = o.object_id
LEFT JOIN (
    SELECT DISTINCT kc.parent_object_id AS object_id
    FROM sys.key_constraints kc
    WHERE kc.type = 'PK'
) pk ON pk.object_id = o.object_id
LEFT JOIN (
    -- dm_db_index_usage_stats 是实例级 DMV，必须按 database_id = DB_ID() 过滤
    -- 取所有索引上的最大时间作为表的"最近被访问"指标
    SELECT
        us.object_id,
        MAX(us.last_user_seek)                                                   AS last_user_seek,
        MAX(us.last_user_scan)                                                   AS last_user_scan,
        MAX(us.last_user_lookup)                                                 AS last_user_lookup,
        MAX(us.last_user_update)                                                 AS last_user_update
    FROM sys.dm_db_index_usage_stats us
    WHERE us.database_id = DB_ID()
    GROUP BY us.object_id
) us ON us.object_id = o.object_id
LEFT JOIN (
    {stats_outdated_sql}
) soc ON soc.object_id = o.object_id
WHERE o.type = 'U'
  AND o.is_ms_shipped = 0
  {schema_filter}
  {table_filter}
ORDER BY {order_by_clause}
""".strip()


def _normalize_limit(limit: Optional[int]) -> int:
    """把外部传入的 limit 收敛到 [1, MAX_LIMIT] 区间，None/非法值用默认值。"""
    if limit is None:
        return DEFAULT_LIMIT
    try:
        v = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    if v <= 0:
        return DEFAULT_LIMIT
    return min(v, MAX_LIMIT)


def _normalize_verbose(verbose: Optional[str]) -> str:
    """收敛 verbose 到合法枚举；None/空串/非法值回落到 summary。

    采用容错回落而非抛错，理由：本工具被 LLM 串联调用，参数偶发拼写错误时
    宁可降级为更省 token 的 summary，也不要中断整条工具链。
    """
    if not verbose:
        return VERBOSE_SUMMARY
    v = str(verbose).strip().lower()
    return v if v in ALLOWED_VERBOSE else VERBOSE_SUMMARY


def _normalize_order_by(order_by: Optional[str]) -> str:
    """收敛 order_by 到合法白名单键；None/空串/非法值回落到 DEFAULT_ORDER_BY。

    严格白名单，避免外部字符串拼接到 SQL 中导致注入。
    """
    if not order_by:
        return DEFAULT_ORDER_BY
    v = str(order_by).strip().lower()
    return v if v in ALLOWED_ORDER_BY else DEFAULT_ORDER_BY


def _normalize_order(order: Optional[str]) -> str:
    """收敛 order 到 asc/desc；None/空串/非法值回落到 DEFAULT_ORDER（desc）。"""
    if not order:
        return DEFAULT_ORDER
    v = str(order).strip().lower()
    return v if v in ALLOWED_ORDER else DEFAULT_ORDER


def _build_order_by_clause(order_by: str, order: str) -> str:
    """根据已规范化的 order_by/order 生成完整的 ORDER BY 子句。

    - 主排序键来自 ALLOWED_ORDER_BY 白名单（不会拼接外部字符串到 SQL）
    - 用 o.name ASC 作为稳定 tie-breaker，保证同值表的输出顺序确定
    - 调用方需保证 order_by/order 均已通过 _normalize_* 规范化
    """
    sql_expr = ALLOWED_ORDER_BY[order_by]
    direction = "DESC" if order == ORDER_DESC else "ASC"
    return f"{sql_expr} {direction}, o.name ASC"


def _project_rows(rows: List[Dict], verbose: str) -> List[Dict]:
    """按 verbose 模式投影输出字段。

    - detail：原样返回（含 20 个字段）
    - summary：只保留 SUMMARY_FIELDS 中 4 个 L1 字段，token 量大幅压缩
    """
    if verbose == VERBOSE_DETAIL:
        return rows
    return [{k: r.get(k) for k in SUMMARY_FIELDS} for r in rows]


def sqlserver_list_table_status(
    cluster_domain: str,
    dbname: str,
    address: Optional[str] = None,
    schema: Optional[str] = None,
    table_name: Optional[str] = None,
    limit: Optional[int] = None,
    verbose: Optional[str] = None,
    order_by: Optional[str] = None,
    order: Optional[str] = None,
) -> Dict:
    """列出业务库下用户表的状态信息（行数/大小/最近活跃/统计过期度）。

    用于在精细分析（get_table_schema 等）之前先定位"值得分析的表"。

    使用通道：sqlserver_data_read_rpc（业务库只读 + VIEW SERVER STATE）

    :param cluster_domain: 集群不可变域名
    :param dbname:         目标业务库名（白名单校验）
    :param address:        可选实例地址；不传时缺省走 master
    :param schema:         可选 schema 过滤；不传则返回所有 schema 下的用户表
    :param table_name:     可选表名精确过滤（白名单校验）；传入后等价于
                           "查这一张表的状态"，limit 自动收敛为 1，
                           表不存在时返回 tables=[] 而非抛异常
    :param limit:          返回前 N 条（按排序键截取），缺省 200，最大 1000；
                           传入 table_name 或 verbose=count_only 时此参数被忽略
    :param verbose:        输出粒度，三态枚举（互斥）：
                           - "summary"（默认）：仅 4 个 L1 字段（schema_name/table_name/
                             row_count/total_size_mb），token 友好
                           - "detail"：全部 20 个字段，索引分析等深度场景
                           - "count_only"：跳过大 SQL，仅返回 total_user_table_count，
                             tables 为空数组、limit 置 0；用于回答
                             "这个库（或 schema）一共有多少张用户表"；
                             此模式下 order_by / order 静默忽略
                           非法值容错回落到 summary，不抛异常
    :param order_by:       排序键（严格白名单，互斥），缺省 total_size_mb：
                           - total_size_mb        ：找大表（最常见入口）
                           - row_count            ：找行数最多 / 最少的表
                           - index_size_mb        ：找索引膨胀的表
                           - stats_outdated_count ：找统计过期最严重的表
                           - last_user_update     ：按写入活跃度排序
                           非白名单值容错回落到 total_size_mb；verbose=count_only 时静默忽略
    :param order:          排序方向，"desc"（默认）或 "asc"；非法值回落到 desc；
                           主排序并列时统一以 o.name ASC 兜底（稳定输出）
    :return: {
        "cluster_domain", "address", "role", "dbname",
        "schema_filter":  传入的 schema（None 表示未过滤）,
        "table_filter":   传入的 table_name（None 表示未过滤）,
        "verbose":        实际生效的 verbose 模式（summary / detail / count_only）,
        "order_by":       实际生效的排序键（verbose=count_only 时为 None）,
        "order":          实际生效的排序方向（verbose=count_only 时为 None）,
        "limit":          实际生效的 limit（verbose=count_only 时为 0）,
        "table_count":    本次返回的明细条数（verbose=count_only 时为 0）,
        "total_user_table_count": 当前库（叠加过滤条件）的用户表总数；
                          仅 verbose=count_only 时填充实际值，其他模式为 None,
        "tables": [
            # detail 模式
            {
                "schema_name", "table_name", "object_id",
                "create_date", "modify_date",
                "is_heap", "index_count", "partition_count", "has_primary_key",
                "row_count", "total_size_mb", "data_size_mb", "index_size_mb",
                "last_user_seek", "last_user_scan",
                "last_user_lookup", "last_user_update",
                "total_modification_counter", "stats_outdated_count",
            }
            # summary 模式（默认）
            { "schema_name", "table_name", "row_count", "total_size_mb" }
            # count_only 模式：tables 为空数组
        ],
    }
    """
    # 库名走白名单 + [] 包裹（用于 USE）；表/schema 不参与本工具的标识符拼接
    quoted_db, _, _ = quote_table_idents(dbname, "dbo", "_dummy_")

    # schema 过滤是可选的，传了就走白名单
    schema_filter_sql = ""
    if schema:
        # 仅做合法性校验（防 SQL 注入），实际拼到 N'...' 字面值里
        quote_sqlserver_ident(schema)
        schema_filter_sql = f"AND s.name = N'{schema}'"

    # table_name 过滤是可选的，传了就走白名单；命中至多一行
    table_filter_sql = ""
    safe_limit_for_detail: int
    if table_name:
        quote_sqlserver_ident(table_name)
        table_filter_sql = f"AND o.name = N'{table_name}'"
        # 单表场景没必要 TOP N，统一为 1，便于阅读输出
        safe_limit_for_detail = 1
    else:
        safe_limit_for_detail = _normalize_limit(limit)

    # 先把 verbose 收敛到合法枚举（含 count_only 第三态），后续按它分支
    normalized_verbose = _normalize_verbose(verbose)

    bk_cloud_id, target = resolve_target_instance(cluster_domain, address)

    # 公共出参骨架，三种模式共用
    base_result: Dict = {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "dbname": dbname,
        "schema_filter": schema,
        "table_filter": table_name,
        "verbose": normalized_verbose,
    }

    # 分支 1：verbose=count_only —— 跳过大 SQL，只跑一条 COUNT(*)
    # 比大 SQL 快 1~2 个数量级，用于"这个库到底有多少张表"
    # 此分支 order_by / order 均无意义，静默忽略
    if normalized_verbose == VERBOSE_COUNT_ONLY:
        count_sql = _LIST_TABLE_STATUS_COUNT_SQL_TEMPLATE.format(
            schema_filter=schema_filter_sql,
            table_filter=table_filter_sql,
        )
        count_rows: List[Dict] = run_user_db_read(
            bk_cloud_id, target["address"], quoted_db, count_sql, "list_table_status_count"
        )
        # 极端兜底：DRS 正常返回必然有 1 行
        total = int(count_rows[0]["total_user_table_count"]) if count_rows else 0

        base_result.update(
            {
                "order_by": None,  # count_only 不涉及排序
                "order": None,
                "limit": 0,  # 本模式不返回明细，置 0 清晰表达
                "table_count": 0,
                "total_user_table_count": total,
                "tables": [],
            }
        )
        return base_result

    # 分支 2：常规明细查询（summary / detail）
    # 排序参数走白名单收敛 + 拼装，杜绝外部字符串注入
    normalized_order_by = _normalize_order_by(order_by)
    normalized_order = _normalize_order(order)
    order_by_clause = _build_order_by_clause(normalized_order_by, normalized_order)

    select_sql = _LIST_TABLE_STATUS_SQL_TEMPLATE.format(
        stats_outdated_sql=build_stats_outdated_sql(),
        limit=safe_limit_for_detail,
        schema_filter=schema_filter_sql,
        table_filter=table_filter_sql,
        order_by_clause=order_by_clause,
    )
    rows: List[Dict] = run_user_db_read(bk_cloud_id, target["address"], quoted_db, select_sql, "list_table_status")
    projected_rows = _project_rows(rows, normalized_verbose)

    base_result.update(
        {
            "order_by": normalized_order_by,
            "order": normalized_order,
            "limit": safe_limit_for_detail,
            "table_count": len(projected_rows),
            "total_user_table_count": None,  # 非 count_only 模式不查总数
            "tables": projected_rows,
        }
    )
    return base_result
