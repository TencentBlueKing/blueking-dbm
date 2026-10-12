# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_MAX_ROWS
from backend.dbm_aiagent.mcp_tools.oracle.helpers.oracle_conn import run_queries, run_query

# 表空间使用率（含临时表空间可按需扩展）
SQL_TABLESPACE_USAGE = """
SELECT * FROM (
    SELECT
        df.tablespace_name,
        ROUND(df.total_mb, 2)                                 AS total_mb,
        ROUND(df.total_mb - NVL(fs.free_mb, 0), 2)            AS used_mb,
        ROUND(NVL(fs.free_mb, 0), 2)                          AS free_mb,
        ROUND((df.total_mb - NVL(fs.free_mb, 0)) * 100 / df.total_mb, 2) AS used_pct,
        df.max_mb,
        df.autoextensible
    FROM (
        SELECT
            tablespace_name,
            SUM(bytes) / 1024 / 1024                           AS total_mb,
            SUM(DECODE(maxbytes, 0, bytes, maxbytes)) / 1024 / 1024 AS max_mb,
            MAX(autoextensible)                                AS autoextensible
        FROM dba_data_files
        GROUP BY tablespace_name
    ) df
    LEFT JOIN (
        SELECT tablespace_name, SUM(bytes) / 1024 / 1024 AS free_mb
        FROM dba_free_space
        GROUP BY tablespace_name
    ) fs ON df.tablespace_name = fs.tablespace_name
    ORDER BY used_pct DESC
) WHERE ROWNUM <= :row_limit
"""

# Undo 使用率
SQL_UNDO_USAGE = """
SELECT
    tablespace_name,
    status,
    SUM(bytes) / 1024 / 1024 AS size_mb,
    COUNT(*)                 AS extent_count
FROM dba_undo_extents
GROUP BY tablespace_name, status
ORDER BY tablespace_name, status
"""

# SGA / PGA 使用
SQL_SGA = """
SELECT name, ROUND(value / 1024 / 1024, 2) AS value_mb
FROM v$sga
"""

SQL_PGA = """
SELECT name, ROUND(value / 1024 / 1024, 2) AS value_mb
FROM v$pgastat
WHERE name IN (
    'total PGA inuse',
    'total PGA allocated',
    'maximum PGA allocated',
    'aggregate PGA target parameter',
    'aggregate PGA auto target'
)
"""


def get_tablespace_usage(addr: str, limit: int = ORACLE_MAX_ROWS) -> dict:
    limit = min(int(limit or ORACLE_MAX_ROWS), ORACLE_MAX_ROWS)
    rows = run_query(addr, SQL_TABLESPACE_USAGE, {"row_limit": limit})
    return {"tablespaces": rows, "count": len(rows)}


def get_undo_usage(addr: str) -> dict:
    rows = run_query(addr, SQL_UNDO_USAGE)
    return {"undo_extents": rows}


def get_sga_pga_usage(addr: str) -> dict:
    sga, pga = run_queries(addr, [(SQL_SGA, None), (SQL_PGA, None)])
    return {"sga": sga, "pga": pga}
