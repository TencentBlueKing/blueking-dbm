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
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_text_sanitizer import sanitize_rows_sql_text

# SQL 文本截断长度，与 blocking_sessions 保持一致
_SQL_TEXT_LIMIT = 256

# order_by 入参 → DMV 列名 的白名单映射，避免任意列名注入到 ORDER BY
_ORDER_BY_COLUMN_MAP = {
    "cpu": "r.cpu_time",
    "duration": "r.total_elapsed_time",
    "reads": "r.logical_reads",
    "writes": "r.writes",
}


def _build_top_requests_sql(top: int, order_by_column: str) -> str:
    """构建 top_requests SQL；过滤掉系统会话（session_id <= 50）。"""
    return f"""
SELECT TOP ({top})
    r.session_id                                 AS session_id,
    r.status                                     AS status,
    r.command                                    AS command,
    r.blocking_session_id                        AS blocking_session_id,
    r.wait_type                                  AS wait_type,
    r.wait_time                                  AS wait_time_ms,
    r.cpu_time                                   AS cpu_time_ms,
    r.total_elapsed_time                         AS elapsed_time_ms,
    r.reads                                      AS reads,
    r.writes                                     AS writes,
    r.logical_reads                              AS logical_reads,
    r.row_count                                  AS row_count,
    DB_NAME(r.database_id)                       AS database_name,
    s.login_name                                 AS login_name,
    s.host_name                                  AS host_name,
    s.program_name                               AS program_name,
    LEFT(SUBSTRING(t.text,
        (r.statement_start_offset / 2) + 1,
        ((CASE r.statement_end_offset
            WHEN -1 THEN DATALENGTH(t.text)
            ELSE r.statement_end_offset END
          - r.statement_start_offset) / 2) + 1
    ), {_SQL_TEXT_LIMIT}) AS sql_text,
    CASE WHEN DATALENGTH(t.text) > {_SQL_TEXT_LIMIT} THEN 1 ELSE 0 END AS sql_text_truncated
FROM sys.dm_exec_requests r
LEFT JOIN sys.dm_exec_sessions s ON s.session_id = r.session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.session_id > 50
  AND r.session_id <> @@SPID
ORDER BY {order_by_column} DESC
""".strip()


def sqlserver_top_requests(
    cluster_domain: str,
    address: Optional[str] = None,
    top: int = 20,
    order_by: str = "cpu",
) -> Dict:
    """查询当前活跃请求 TOP N（按 cpu/duration/reads/writes 排序）。

    使用通道：sqlserver_sys_read_rpc。

    :param cluster_domain: 集群不可变域名
    :param address: 可选，指定具体实例；不传则缺省查询 master
    :param top: 返回条数
    :param order_by: 排序维度，仅允许 "cpu" / "duration" / "reads" / "writes"
    :return: {
        "cluster_domain": "...",
        "address": "ip:port",
        "role": "...",
        "order_by": "...",
        "top_requests": [...]
    }
    """
    if top <= 0 or top > 100:
        raise DBMMcpBaseException(msg="top must be in (0, 100]")

    order_by_column = _ORDER_BY_COLUMN_MAP.get(order_by)
    if not order_by_column:
        raise DBMMcpBaseException(msg=f"invalid order_by: {order_by}, allowed: {list(_ORDER_BY_COLUMN_MAP)}")

    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )
    target = instances[0]

    rpc_results = DRSApi.sqlserver_sys_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [target["address"]],
            "cmds": [_build_top_requests_sql(top, order_by_column)],
        }
    )

    rpc_res = rpc_results[0]
    if rpc_res.get("error_msg"):
        raise DBMMcpBaseException(msg=rpc_res["error_msg"])

    cmd_res = rpc_res["cmd_results"][0]
    if cmd_res.get("error_msg"):
        raise DBMMcpBaseException(msg=cmd_res["error_msg"])

    top_requests = cmd_res.get("table_data") or []
    # 对 sql_text 做脱敏：SP 调用全参数打掉；普通 SQL 仅脱敏手机号/身份证/邮箱/password=
    sanitize_rows_sql_text(top_requests)

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "order_by": order_by,
        "top_requests": top_requests,
    }
