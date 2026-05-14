# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

P0 - get_table_schema：表结构（列、类型、可空、计算列、默认/检查约束、主外键）

设计要点：
  - 一次性返回"分析所需"的最小完整集，避免 Agent 二次发问
  - 类型字符串拼好（例如 NVARCHAR(50) / DECIMAL(18,2) / VARCHAR(MAX)），LLM 可直接消费
  - 计算列与持久化标识、IDENTITY、ROWVERSION 都给出
  - 主外键单独输出，便于和索引/JOIN 分析对齐
  - 入参 tables 支持批量；每张表独立容错（status=ok / not_found），不会因为一张表
    不存在而让整批失败
"""
from typing import Dict, List, Optional

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.common import DEFAULT_SCHEMA

# ------- 列信息 SQL -------
# 说明：
#   - 类型字符串按 system_type 名 + 长度/精度 拼接，char/varchar/binary 等显示长度，
#     numeric/decimal 显示 (precision, scale)；length=-1 时输出 (MAX)
#   - is_computed=1 时拼出 computed_definition 与是否持久化
#   - default_definition 来自 sys.default_constraints
_COLUMNS_SQL_TEMPLATE = """
SELECT
    c.column_id                                      AS column_id,
    c.name                                           AS column_name,
    t.name                                           AS type_name,
    CASE
        WHEN t.name IN (N'nchar', N'nvarchar')
            THEN t.name +
                 CASE WHEN c.max_length = -1 THEN N'(MAX)'
                      ELSE N'(' + CAST(c.max_length / 2 AS NVARCHAR(10)) + N')' END
        WHEN t.name IN (N'char', N'varchar', N'binary', N'varbinary')
            THEN t.name +
                 CASE WHEN c.max_length = -1 THEN N'(MAX)'
                      ELSE N'(' + CAST(c.max_length AS NVARCHAR(10)) + N')' END
        WHEN t.name IN (N'decimal', N'numeric')
            THEN t.name + N'(' + CAST(c.precision AS NVARCHAR(10))
                 + N',' + CAST(c.scale AS NVARCHAR(10)) + N')'
        WHEN t.name IN (N'datetime2', N'time', N'datetimeoffset')
            THEN t.name + N'(' + CAST(c.scale AS NVARCHAR(10)) + N')'
        ELSE t.name
    END                                              AS type_display,
    c.max_length                                     AS max_length,
    c.precision                                      AS precision,
    c.scale                                          AS scale,
    c.is_nullable                                    AS is_nullable,
    c.is_identity                                    AS is_identity,
    c.is_computed                                    AS is_computed,
    cc.is_persisted                                  AS is_persisted,
    cc.definition                                    AS computed_definition,
    c.is_rowguidcol                                  AS is_rowguidcol,
    CASE WHEN c.system_type_id IN (189) THEN 1 ELSE 0 END AS is_rowversion,  -- timestamp/rowversion
    dc.definition                                    AS default_definition,
    c.collation_name                                 AS collation
FROM sys.columns c
JOIN sys.objects o            ON o.object_id = c.object_id
JOIN sys.schemas s            ON s.schema_id = o.schema_id
JOIN sys.types   t            ON t.user_type_id = c.user_type_id
LEFT JOIN sys.computed_columns cc  ON cc.object_id = c.object_id AND cc.column_id = c.column_id
LEFT JOIN sys.default_constraints dc ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
ORDER BY c.column_id
""".strip()


# ------- 主键 SQL -------
# 通过 sys.indexes.is_primary_key=1 + sys.index_columns 取出主键列；按 key_ordinal 排序
_PRIMARY_KEY_SQL_TEMPLATE = """
SELECT
    i.name                                  AS pk_name,
    i.type_desc                             AS pk_type,
    ic.key_ordinal                          AS key_ordinal,
    c.name                                  AS column_name
FROM sys.indexes i
JOIN sys.objects o       ON o.object_id = i.object_id
JOIN sys.schemas s       ON s.schema_id = o.schema_id
JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
JOIN sys.columns c        ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
  AND i.is_primary_key = 1
ORDER BY ic.key_ordinal
""".strip()


# ------- 外键 SQL -------
# 一行一列，便于 LLM 处理多列外键场景
_FOREIGN_KEY_SQL_TEMPLATE = """
SELECT
    fk.name                                          AS fk_name,
    rs.name                                          AS referenced_schema,
    ro.name                                          AS referenced_table,
    fkc.constraint_column_id                         AS column_ordinal,
    pc.name                                          AS column_name,
    rc.name                                          AS referenced_column,
    fk.delete_referential_action_desc                AS on_delete,
    fk.update_referential_action_desc                AS on_update,
    fk.is_disabled                                   AS is_disabled,
    fk.is_not_trusted                                AS is_not_trusted
FROM sys.foreign_keys fk
JOIN sys.objects o          ON o.object_id = fk.parent_object_id
JOIN sys.schemas s          ON s.schema_id = o.schema_id
JOIN sys.objects ro         ON ro.object_id = fk.referenced_object_id
JOIN sys.schemas rs         ON rs.schema_id = ro.schema_id
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns pc         ON pc.object_id = fkc.parent_object_id     AND pc.column_id = fkc.parent_column_id
JOIN sys.columns rc         ON rc.object_id = fkc.referenced_object_id AND rc.column_id = fkc.referenced_column_id
WHERE o.type = 'U'
  AND s.name = N'{schema}'
  AND o.name = N'{table}'
ORDER BY fk.name, fkc.constraint_column_id
""".strip()


def _build_pk_for_one(rows: List[Dict]) -> Optional[Dict]:
    if not rows:
        return None
    return {
        "name": rows[0].get("pk_name"),
        "type": rows[0].get("pk_type"),
        "columns": [r.get("column_name") for r in rows],
    }


def _aggregate_fk(rows: List[Dict]) -> List[Dict]:
    fk_map: Dict[str, Dict] = {}
    for r in rows:
        fk_name = r.get("fk_name")
        bucket = fk_map.setdefault(
            fk_name,
            {
                "name": fk_name,
                "referenced_schema": r.get("referenced_schema"),
                "referenced_table": r.get("referenced_table"),
                "on_delete": r.get("on_delete"),
                "on_update": r.get("on_update"),
                "is_disabled": r.get("is_disabled"),
                "is_not_trusted": r.get("is_not_trusted"),
                "columns": [],
                "referenced_columns": [],
            },
        )
        bucket["columns"].append(r.get("column_name"))
        bucket["referenced_columns"].append(r.get("referenced_column"))
    return list(fk_map.values())


def _query_one_table_schema(
    bk_cloud_id: int,
    address: str,
    quoted_db: str,
    schema: str,
    table: str,
) -> Dict:
    """单表查询：返回 {columns, primary_key, foreign_keys}。

    若列查询为空（表不存在或无列），抛 DBMMcpBaseException 由外层转为 not_found。
    """
    columns_sql = _COLUMNS_SQL_TEMPLATE.format(schema=schema, table=table)
    columns = run_user_db_read(bk_cloud_id, address, quoted_db, columns_sql, "get_table_schema(columns)")
    if not columns:
        raise DBMMcpBaseException(msg=f"table not found or no columns: [{schema}].[{table}]")

    pk_sql = _PRIMARY_KEY_SQL_TEMPLATE.format(schema=schema, table=table)
    pk_rows = run_user_db_read(bk_cloud_id, address, quoted_db, pk_sql, "get_table_schema(primary_key)")

    fk_sql = _FOREIGN_KEY_SQL_TEMPLATE.format(schema=schema, table=table)
    fk_rows = run_user_db_read(bk_cloud_id, address, quoted_db, fk_sql, "get_table_schema(foreign_keys)")

    return {
        "columns": columns,
        "primary_key": _build_pk_for_one(pk_rows),
        "foreign_keys": _aggregate_fk(fk_rows),
    }


def sqlserver_get_table_schema(
    cluster_domain: str,
    dbname: str,
    tables: List[str],
    schema: str = DEFAULT_SCHEMA,
    address: Optional[str] = None,
) -> Dict:
    """批量获取表结构（列、主键、外键）。

    数据源：sys.columns / sys.types / sys.computed_columns / sys.default_constraints
            / sys.indexes(is_primary_key=1) / sys.foreign_keys
    使用通道：sqlserver_data_read_rpc（业务库只读账号）

    :param cluster_domain: 集群不可变域名
    :param dbname: 目标数据库名（白名单校验）
    :param tables: 目标表名列表（1~20 个，整批共用同一 schema；列表内重复项会被去重）
    :param schema: 表所在 schema，默认 dbo
    :param address: 可选实例地址；不传时缺省走 master
    :return: {
        "cluster_domain", "address", "role", "dbname", "schema",
        "table_count", "ok_count",
        "results": [
            {"table", "status", "error",
             "columns": [...], "primary_key": {...} | None, "foreign_keys": [...]},
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
        # 单表也跑一次校验，防止个别表名非法导致整批静默失败
        quote_sqlserver_ident(tbl)
        try:
            data = _query_one_table_schema(bk_cloud_id, target["address"], quoted_db, schema, tbl)
            results.append(
                {
                    "table": tbl,
                    "status": "ok",
                    "error": None,
                    "columns": data["columns"],
                    "primary_key": data["primary_key"],
                    "foreign_keys": data["foreign_keys"],
                }
            )
            ok_count += 1
        except DBMMcpBaseException as exc:
            results.append(
                {
                    "table": tbl,
                    "status": "not_found",
                    "error": str(exc),
                    "columns": [],
                    "primary_key": None,
                    "foreign_keys": [],
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
