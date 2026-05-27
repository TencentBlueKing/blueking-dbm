# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

独立 MCP 工具：查询指定数据库的 MDF / LDF 文件容量使用率

设计要点：
  - 入参 databases 支持列表（1~20 个），参考 get_table_schema 的批量模式
  - 每个库独立容错（status=ok / offline / error），不会因为一个库失败让整批失败
  - 使用 FILEPROPERTY(name, 'SpaceUsed') 获取已用空间，需要在对应库上下文中执行
  - 同时返回文件级明细和库级汇总使用率（data_used_pct / log_used_pct）
  - 使用通道：sqlserver_data_read_rpc（业务库只读账号）
"""
from typing import Dict, List, Optional

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident

# 查询单个库的文件使用率 SQL
# sys.database_files 在当前库上下文中可用
# FILEPROPERTY(name, 'SpaceUsed') 返回已用页数（8KB/页）
# file type 含义: 0=ROWS(mdf/ndf), 1=LOG(ldf)
_FILE_USAGE_SQL = """
SELECT
    f.file_id                                        AS file_id,
    f.name                                           AS file_name,
    f.type                                           AS file_type,
    CASE f.type WHEN 0 THEN N'ROWS' WHEN 1 THEN N'LOG' ELSE N'OTHER' END AS file_type_desc,
    f.physical_name                                  AS physical_name,
    CAST(f.size AS BIGINT) * 8 / 1024                AS allocated_mb,
    CAST(FILEPROPERTY(f.name, 'SpaceUsed') AS BIGINT) * 8 / 1024    AS used_mb,
    CAST(
        CASE WHEN f.size = 0 THEN 0
             ELSE CAST(FILEPROPERTY(f.name, 'SpaceUsed') AS BIGINT) * 100.0 / f.size
        END AS DECIMAL(5,2)
    )                                                AS used_pct,
    CASE f.max_size
        WHEN -1 THEN CAST(-1 AS BIGINT)
        WHEN 0  THEN CAST(f.size AS BIGINT) * 8 / 1024
        ELSE CAST(f.max_size AS BIGINT) * 8 / 1024
    END                                              AS max_size_mb,
    CASE f.growth
        WHEN 0 THEN N'NONE'
        ELSE
            CASE f.is_percent_growth
                WHEN 1 THEN CAST(f.growth AS NVARCHAR(10)) + N'%'
                ELSE CAST(CAST(f.growth AS BIGINT) * 8 / 1024 AS NVARCHAR(20)) + N'MB'
            END
    END                                              AS growth_desc
FROM sys.database_files f
WHERE f.type IN (0, 1)
ORDER BY f.type, f.file_id
""".strip()


def _compute_summary(files: List[Dict]) -> Dict:
    """根据文件明细计算库级汇总使用率。"""
    data_allocated = 0
    data_used = 0
    log_allocated = 0
    log_used = 0

    for f in files:
        allocated = f.get("allocated_mb") or 0
        used = f.get("used_mb") or 0
        if f.get("file_type") == 0:
            data_allocated += allocated
            data_used += used
        elif f.get("file_type") == 1:
            log_allocated += allocated
            log_used += used

    data_used_pct = round(data_used * 100.0 / data_allocated, 2) if data_allocated > 0 else 0.0
    log_used_pct = round(log_used * 100.0 / log_allocated, 2) if log_allocated > 0 else 0.0

    return {
        "data_allocated_mb": data_allocated,
        "data_used_mb": data_used,
        "data_used_pct": data_used_pct,
        "log_allocated_mb": log_allocated,
        "log_used_mb": log_used,
        "log_used_pct": log_used_pct,
    }


def _query_one_database_file_usage(
    bk_cloud_id: int,
    address: str,
    dbname: str,
) -> Dict:
    """查询单个库的文件使用率。

    若查询失败（库 OFFLINE/RESTORING 等），抛 DBMMcpBaseException 由外层转为 error。
    """
    quoted_db = quote_sqlserver_ident(dbname)
    files = run_user_db_read(bk_cloud_id, address, quoted_db, _FILE_USAGE_SQL, "database_file_usage")
    if not files:
        raise DBMMcpBaseException(msg=f"no file info returned for database: [{dbname}]")

    summary = _compute_summary(files)
    return {
        "files": files,
        **summary,
    }


def sqlserver_database_file_usage(
    cluster_domain: str,
    databases: List[str],
    address: Optional[str] = None,
) -> Dict:
    """批量查询数据库文件（MDF/LDF）容量使用率。

    数据源：sys.database_files + FILEPROPERTY(name, 'SpaceUsed')
    使用通道：sqlserver_data_read_rpc（业务库只读账号）

    :param cluster_domain: 集群不可变域名
    :param databases: 目标数据库名列表（1~20 个；列表内重复项会被去重）
    :param address: 可选实例地址；不传时缺省走 master
    :return: {
        "cluster_domain", "address", "role",
        "database_count", "ok_count",
        "results": [
            {
                "database": "...",
                "status": "ok" | "error",
                "error": null | "...",
                "files": [...],
                "data_allocated_mb", "data_used_mb", "data_used_pct",
                "log_allocated_mb", "log_used_mb", "log_used_pct",
            }, ...
        ],
    }
    """
    # 去重并保持顺序
    unique_databases = list(dict.fromkeys(databases))

    bk_cloud_id, target = resolve_target_instance(cluster_domain, address)

    results: List[Dict] = []
    ok_count = 0
    for dbname in unique_databases:
        # 校验库名合法性
        try:
            quote_sqlserver_ident(dbname)
        except DBMMcpBaseException as exc:
            results.append(
                {
                    "database": dbname,
                    "status": "error",
                    "error": str(exc),
                    "files": [],
                    "data_allocated_mb": 0,
                    "data_used_mb": 0,
                    "data_used_pct": None,
                    "log_allocated_mb": 0,
                    "log_used_mb": 0,
                    "log_used_pct": None,
                }
            )
            continue

        try:
            data = _query_one_database_file_usage(bk_cloud_id, target["address"], dbname)
            results.append(
                {
                    "database": dbname,
                    "status": "ok",
                    "error": None,
                    **data,
                }
            )
            ok_count += 1
        except DBMMcpBaseException as exc:
            results.append(
                {
                    "database": dbname,
                    "status": "error",
                    "error": str(exc),
                    "files": [],
                    "data_allocated_mb": 0,
                    "data_used_mb": 0,
                    "data_used_pct": None,
                    "log_allocated_mb": 0,
                    "log_used_mb": 0,
                    "log_used_pct": None,
                }
            )

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "database_count": len(unique_databases),
        "ok_count": ok_count,
        "results": results,
    }
