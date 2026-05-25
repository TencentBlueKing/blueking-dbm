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
from typing import Dict, Optional

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_sqlserver_addresses

# 排序键白名单：仅暴露体积类 3 个排序键，避免 LLM 误用
# - total_size_mb：data + log 总占用（默认，最常见“找大库”场景）
# - data_size_mb：仅数据文件占用
# - log_size_mb：仅日志文件占用（排查日志暴涨）
#
# 关键约束：SQL Server 的 ORDER BY 中，**表达式里的标识符必须是真实列**，
# 不能引用 SELECT 列表里 SUM(...) AS xxx 的别名（单独引用别名是允许的，
# 但放进 (alias_a + alias_b) 这种算术表达式中就会报 "Invalid column name"）。
# 因此 total_size_mb 的排序键必须重写完整的 SUM 表达式，
# 而 data_size_mb / log_size_mb 是单别名引用，可以直接用。
_TOTAL_SIZE_EXPR = (
    "(ISNULL(SUM(CASE WHEN mf.type = 0 THEN mf.size END), 0)"
    " + ISNULL(SUM(CASE WHEN mf.type = 1 THEN mf.size END), 0))"
)
_ORDER_BY_MAP = {
    "total_size_mb": _TOTAL_SIZE_EXPR,
    "data_size_mb": "data_size_mb",
    "log_size_mb": "log_size_mb",
}
_ORDER_MAP = {"asc": "ASC", "desc": "DESC"}

# 数据库清单查询 SQL：基于 sys.databases + sys.master_files 聚合每个库的数据/日志大小
# size 列单位是 8KB 页，乘 8 转 KB；这里直接折算为 MB 便于阅读
# ORDER BY 子句通过白名单校验后由 Python 端拼入，杜绝注入
_LIST_DATABASES_SQL = """
SELECT
    d.database_id,
    d.name                                AS database_name,
    d.state_desc                          AS state,
    d.recovery_model_desc                 AS recovery_model,
    d.compatibility_level                 AS compatibility_level,
    d.collation_name                      AS collation,
    d.create_date                         AS create_date,
    d.is_read_only                        AS is_read_only,
    ISNULL(SUM(CASE WHEN mf.type = 0 THEN mf.size END) * 8 / 1024, 0) AS data_size_mb,
    ISNULL(SUM(CASE WHEN mf.type = 1 THEN mf.size END) * 8 / 1024, 0) AS log_size_mb
FROM sys.databases d
LEFT JOIN sys.master_files mf ON mf.database_id = d.database_id
GROUP BY
    d.database_id, d.name, d.state_desc, d.recovery_model_desc,
    d.compatibility_level, d.collation_name, d.create_date, d.is_read_only
{order_by_clause}
""".strip()


def _build_order_by_clause(order_by: str, order: str) -> str:
    """根据白名单构建 ORDER BY 子句；非法值直接抛异常。

    所有排序都追加 `, d.database_id ASC` 作为稳定 tie-breaker，
    避免体积并列（例如多个 0MB 空库）时返回顺序抖动。
    """
    if order_by not in _ORDER_BY_MAP:
        raise DBMMcpBaseException(msg=f"invalid order_by={order_by}, must be one of {list(_ORDER_BY_MAP.keys())}")
    if order not in _ORDER_MAP:
        raise DBMMcpBaseException(msg=f"invalid order={order}, must be one of {list(_ORDER_MAP.keys())}")
    return f"ORDER BY {_ORDER_BY_MAP[order_by]} {_ORDER_MAP[order]}, d.database_id ASC"


def sqlserver_list_databases(
    cluster_domain: str,
    address: Optional[str] = None,
    order_by: str = "total_size_mb",
    order: str = "desc",
) -> Dict:
    """查询 sqlserver 实例上的数据库清单（含状态、恢复模式、数据/日志大小）。

    使用通道：sqlserver_sys_read_rpc。

    :param cluster_domain: 集群不可变域名
    :param address: 可选，指定具体实例；不传则查询集群内全部实例
    :param order_by: 排序键，可选 total_size_mb / data_size_mb / log_size_mb，默认 total_size_mb
    :param order: 排序方向，asc / desc，默认 desc
    :return: {
        "cluster_domain": "...",
        "results": [
            {
                "address": "ip:port",
                "role": "...",
                "is_stand_by": bool,
                "databases": [ ...每行一个库... ],
                "database_count": N,
                "error_msg": ""
            }, ...
        ]
    }
    """
    sql = _LIST_DATABASES_SQL.format(order_by_clause=_build_order_by_clause(order_by, order))

    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )

    rpc_results = DRSApi.sqlserver_sys_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [item["address"] for item in instances],
            "cmds": [sql],
        }
    )
    address_to_rpc = {res["address"]: res for res in rpc_results}

    results = []
    for item in instances:
        rpc_res = address_to_rpc.get(item["address"])
        if rpc_res is None:
            results.append({**item, "databases": [], "database_count": 0, "error_msg": "no rpc response"})
            continue

        if rpc_res.get("error_msg"):
            results.append({**item, "databases": [], "database_count": 0, "error_msg": rpc_res["error_msg"]})
            continue

        cmd_res = rpc_res["cmd_results"][0]
        if cmd_res.get("error_msg"):
            results.append({**item, "databases": [], "database_count": 0, "error_msg": cmd_res["error_msg"]})
            continue

        databases = cmd_res.get("table_data") or []
        results.append(
            {
                **item,
                "databases": databases,
                "database_count": len(databases),
                "error_msg": "",
            }
        )

    if not results:
        raise DBMMcpBaseException(msg="no instance result returned")

    return {"cluster_domain": cluster_domain, "results": results}
