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

# SQL 文本截断长度（与 top_requests 保持一致；后续可统一调整）
_SQL_TEXT_LIMIT = 256

# 阻塞会话查询：列出当前所有"被阻塞"的请求及其阻塞源
# - r.blocking_session_id != 0 表示该请求正在等待其他 session 释放资源
# - 通过 OUTER APPLY sys.dm_exec_sql_text 拿 SQL 文本头部
# - LEFT JOIN sys.dm_exec_sessions 拿到阻塞源会话的登录名/host
_BLOCKING_SQL = """
SELECT TOP ({top})
    r.session_id                                 AS session_id,
    r.blocking_session_id                        AS blocking_session_id,
    r.status                                     AS status,
    r.command                                    AS command,
    r.wait_type                                  AS wait_type,
    r.wait_time                                  AS wait_time_ms,
    r.wait_resource                              AS wait_resource,
    r.cpu_time                                   AS cpu_time_ms,
    r.total_elapsed_time                         AS elapsed_time_ms,
    r.reads                                      AS reads,
    r.writes                                     AS writes,
    r.logical_reads                              AS logical_reads,
    DB_NAME(r.database_id)                       AS database_name,
    s.login_name                                 AS login_name,
    s.host_name                                  AS host_name,
    s.program_name                               AS program_name,
    bs.login_name                                AS blocker_login_name,
    bs.host_name                                 AS blocker_host_name,
    bs.program_name                              AS blocker_program_name,
    LEFT(SUBSTRING(t.text,
        (r.statement_start_offset / 2) + 1,
        ((CASE r.statement_end_offset
            WHEN -1 THEN DATALENGTH(t.text)
            ELSE r.statement_end_offset END
          - r.statement_start_offset) / 2) + 1
    ), {limit}) AS sql_text,
    CASE WHEN DATALENGTH(t.text) > {limit} THEN 1 ELSE 0 END AS sql_text_truncated
FROM sys.dm_exec_requests r
LEFT JOIN sys.dm_exec_sessions s  ON s.session_id  = r.session_id
LEFT JOIN sys.dm_exec_sessions bs ON bs.session_id = r.blocking_session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.blocking_session_id <> 0
ORDER BY r.wait_time DESC
""".strip()


def sqlserver_blocking_sessions(
    cluster_domain: str,
    address: Optional[str] = None,
    top: int = 20,
) -> Dict:
    """查询当前实例上的阻塞会话快照（被阻塞请求 + 阻塞源信息）。

    使用通道：sqlserver_sys_read_rpc（仅访问 DMV，无需业务库权限）。

    :param cluster_domain: 集群不可变域名
    :param address: 可选，指定具体实例；不传则缺省查询 master
    :param top: 返回条数上限，按 wait_time 倒序
    :return: {
        "cluster_domain": "...",
        "address": "ip:port",
        "role": "...",
        "blocking_count": N,
        "blocking_sessions": [...]
    }
    """
    if top <= 0 or top > 200:
        raise DBMMcpBaseException(msg="top must be in (0, 200]")

    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )
    target = instances[0]

    sql = _BLOCKING_SQL.format(top=top, limit=_SQL_TEXT_LIMIT)

    rpc_results = DRSApi.sqlserver_sys_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [target["address"]],
            "cmds": [sql],
        }
    )

    rpc_res = rpc_results[0]
    if rpc_res.get("error_msg"):
        raise DBMMcpBaseException(msg=rpc_res["error_msg"])

    cmd_res = rpc_res["cmd_results"][0]
    if cmd_res.get("error_msg"):
        raise DBMMcpBaseException(msg=cmd_res["error_msg"])

    blocking_sessions = cmd_res.get("table_data") or []
    # 对 sql_text 做脱敏：SP 调用全参数打掉；普通 SQL 仅脱敏手机号/身份证/邮箱/password=
    sanitize_rows_sql_text(blocking_sessions)
    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "blocking_count": len(blocking_sessions),
        "blocking_sessions": blocking_sessions,
    }
