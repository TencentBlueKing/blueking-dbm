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
from typing import Dict, List, Optional

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_sqlserver_addresses
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_text_sanitizer import is_sp_executesql, sanitize_rows_sql_text

# 单次批量查询的 session_id 上限，避免超长命令列表
_MAX_SESSION_IDS = 100

# event_info（即 DBCC INPUTBUFFER 的 EventInfo）截断长度；避免超长语句撑爆上下文
_MAX_EVENT_INFO_CHARS = 4000


def _build_session_ctx_sql(session_ids: List[int]) -> str:
    """构建会话上下文查询，补齐 login_name / host_name / program_name / database_name。"""
    ids = ", ".join(str(int(s)) for s in session_ids)
    return f"""
SELECT
    s.session_id         AS session_id,
    s.login_name         AS login_name,
    s.host_name          AS host_name,
    s.program_name       AS program_name,
    DB_NAME(s.database_id) AS database_name
FROM sys.dm_exec_sessions s
WHERE s.session_id IN ({ids})
ORDER BY s.session_id
""".strip()


def _build_input_buffer_cmd(session_id: int) -> str:
    """构建单条 DBCC INPUTBUFFER 命令，返回原生 EventType / Parameters / EventInfo。"""
    return f"DBCC INPUTBUFFER({int(session_id)})"


def _is_sp_executesql(event_info: Optional[str]) -> int:
    """从 EventInfo 文本判断是否为 sp_executesql 动态 SQL（大小写不敏感）。"""
    return 1 if is_sp_executesql(event_info) else 0


def sqlserver_input_buffer(
    cluster_domain: str,
    session_ids: List[int],
    address: Optional[str] = None,
    max_event_info_chars: int = _MAX_EVENT_INFO_CHARS,
) -> Dict:
    """查询指定 session 的 input buffer（即 DBCC INPUTBUFFER 的 EventInfo 等价信息）。

    使用通道：sqlserver_sys_read_rpc（仅访问 sys.* DMV，无需业务库权限）。
    通过 DBCC INPUTBUFFER 逐 session 查询，原生返回 EventType / Parameters / EventInfo，
    兼容 SQL Server 2008 / 2012 / 2014 / 2016 / 2017 / 2019 / 2022。

    :param cluster_domain: 集群不可变域名
    :param session_ids: 会话 ID 列表（正整数，1~32767），一次最多 {_MAX_SESSION_IDS} 个
    :param address: 可选，指定具体实例；不传则缺省查询 master
    :param max_event_info_chars: event_info 截断长度（防超长语句），默认 4000
    :return: {
        "cluster_domain": "...",
        "address": "ip:port",
        "role": "...",
        "session_count": N,
        "input_buffers": [
            {
                "session_id": ..., "login_name": ..., "host_name": ...,
                "program_name": ..., "database_name": ...,
                "event_type": "RPC Event" | "Language Event",
                "is_sp_executesql": 0/1,
                "event_info": ..., "event_info_truncated": 0/1
            }, ...
        ]
    }
    """
    # 1. 入参校验
    if not session_ids:
        raise DBMMcpBaseException(msg="session_ids must not be empty")

    # 去重并保持有序
    seen = set()
    dedup_ids = []
    for sid in session_ids:
        if not isinstance(sid, int) or isinstance(sid, bool):
            raise DBMMcpBaseException(msg=f"invalid session_id: {sid}, must be integer")
        if sid < 1 or sid > 32767:
            raise DBMMcpBaseException(msg=f"session_id out of range [1, 32767]: {sid}")
        if sid in seen:
            continue
        seen.add(sid)
        dedup_ids.append(sid)

    if len(dedup_ids) > _MAX_SESSION_IDS:
        raise DBMMcpBaseException(msg=f"session_ids exceeds max batch size {_MAX_SESSION_IDS}")

    if max_event_info_chars < 256 or max_event_info_chars > 32767:
        raise DBMMcpBaseException(msg="max_event_info_chars must be in [256, 32767]")

    # 2. 解析目标实例
    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )
    target = instances[0]

    # 3. 构造 cmds：先查会话上下文，再逐 session 下发 DBCC INPUTBUFFER
    cmds = [_build_session_ctx_sql(dedup_ids)]
    cmds.extend(_build_input_buffer_cmd(sid) for sid in dedup_ids)

    rpc_results = DRSApi.sqlserver_sys_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [target["address"]],
            "cmds": cmds,
        }
    )

    rpc_res = rpc_results[0]
    if rpc_res.get("error_msg"):
        raise DBMMcpBaseException(msg=rpc_res["error_msg"])

    cmd_results = rpc_res.get("cmd_results") or []
    if len(cmd_results) != len(cmds):
        raise DBMMcpBaseException(
            msg=f"unexpected rpc result: expected {len(cmds)} cmd_results, got {len(cmd_results)}"
        )

    # 4. 解析会话上下文（第一条 SELECT）
    ctx_res = cmd_results[0]
    if ctx_res.get("error_msg"):
        raise DBMMcpBaseException(msg=ctx_res["error_msg"])

    session_ctx_map = {}
    for row in ctx_res.get("table_data") or []:
        if isinstance(row, dict) and "session_id" in row:
            session_ctx_map[row["session_id"]] = row

    # 5. 逐 session 解析 DBCC INPUTBUFFER 结果
    input_buffers = []
    for idx, sid in enumerate(dedup_ids):
        cmd_res = cmd_results[idx + 1]
        if cmd_res.get("error_msg"):
            # DBCC 本身报错属于环境/权限问题，整体抛出，避免静默掩盖
            raise DBMMcpBaseException(msg=f"DBCC INPUTBUFFER({sid}) failed: {cmd_res['error_msg']}")

        rows = cmd_res.get("table_data") or []
        # DBCC INPUTBUFFER 返回一行 EventType/Parameters/EventInfo（可能大写列名）
        row = rows[0] if rows else {}
        event_type = row.get("EventType") or row.get("event_type")
        raw_event_info = row.get("EventInfo") or row.get("event_info") or ""

        event_info = raw_event_info[:max_event_info_chars] if raw_event_info else ""
        ctx = session_ctx_map.get(sid, {})

        input_buffers.append(
            {
                "session_id": sid,
                "login_name": ctx.get("login_name"),
                "host_name": ctx.get("host_name"),
                "program_name": ctx.get("program_name"),
                "database_name": ctx.get("database_name"),
                "event_type": event_type,
                "is_sp_executesql": _is_sp_executesql(raw_event_info),
                "event_info": event_info,
                "event_info_truncated": 1 if raw_event_info and len(raw_event_info) > max_event_info_chars else 0,
            }
        )

    # 6. 对 event_info 做脱敏：SP 调用全参数打掉；普通 SQL 仅脱敏手机号/身份证/邮箱/password=
    sanitize_rows_sql_text(input_buffers, fields=("event_info",))

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "session_count": len(input_buffers),
        "input_buffers": input_buffers,
    }
