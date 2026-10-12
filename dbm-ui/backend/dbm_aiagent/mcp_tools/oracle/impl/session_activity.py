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
from backend.dbm_aiagent.mcp_tools.oracle.helpers.oracle_conn import run_query
from backend.dbm_aiagent.mcp_tools.oracle.helpers.time_window import local_to_tz

# 以下查询均带出 child_number，与 sql_id 配对可作为 get_sql_plan 的入参

# 活跃会话（剔除后台进程与空闲等待）
SQL_ACTIVE_SESSIONS = f"""
SELECT * FROM (
    SELECT
        s.sid,
        s.serial#        AS serial_num,
        s.username,
        s.status,
        s.osuser,
        s.machine,
        s.program,
        s.module,
        s.sql_id,
        s.sql_child_number AS child_number,
        s.event,
        s.wait_class,
        s.seconds_in_wait,
        s.state,
        s.blocking_session,
        s.last_call_et,
        {local_to_tz("s.logon_time")} AS logon_time
    FROM v$session s
    WHERE s.type = 'USER'
      AND s.status = 'ACTIVE'
      AND (s.wait_class IS NULL OR s.wait_class <> 'Idle')
    ORDER BY s.last_call_et DESC
) WHERE ROWNUM <= :row_limit
"""

# 阻塞链：有阻塞者的会话 + 被谁阻塞 + 阻塞多久
SQL_BLOCKING_SESSIONS = """
SELECT * FROM (
    SELECT
        blocker.sid                    AS blocker_sid,
        blocker.serial#                AS blocker_serial,
        blocker.username               AS blocker_user,
        blocker.sql_id                 AS blocker_sql_id,
        blocker.sql_child_number       AS blocker_child_number,
        blocker.machine                AS blocker_machine,
        waiter.sid                     AS waiter_sid,
        waiter.serial#                 AS waiter_serial,
        waiter.username                AS waiter_user,
        waiter.sql_id                  AS waiter_sql_id,
        waiter.sql_child_number        AS waiter_child_number,
        waiter.event                   AS waiter_event,
        waiter.seconds_in_wait         AS waiter_seconds_in_wait,
        waiter.blocking_session_status AS waiter_block_status
    FROM v$session waiter
    JOIN v$session blocker ON waiter.blocking_session = blocker.sid
    WHERE waiter.blocking_session IS NOT NULL
    ORDER BY waiter.seconds_in_wait DESC
) WHERE ROWNUM <= :row_limit
"""

# 长时间运行的 SQL（基于 v$session 的 last_call_et，剔除 Idle）
SQL_LONG_RUNNING = """
SELECT * FROM (
    SELECT
        s.sid,
        s.serial#       AS serial_num,
        s.username,
        s.status,
        s.sql_id,
        s.sql_child_number AS child_number,
        s.event,
        s.wait_class,
        s.last_call_et  AS seconds_running,
        s.machine,
        s.program,
        q.sql_text
    FROM v$session s
    LEFT JOIN v$sql q ON s.sql_id = q.sql_id AND s.sql_child_number = q.child_number
    WHERE s.type = 'USER'
      AND s.status = 'ACTIVE'
      AND (s.wait_class IS NULL OR s.wait_class <> 'Idle')
      AND s.last_call_et >= :min_seconds
    ORDER BY s.last_call_et DESC
) WHERE ROWNUM <= :row_limit
"""


def get_active_sessions(addr: str, limit: int = ORACLE_MAX_ROWS) -> dict:
    limit = min(int(limit or ORACLE_MAX_ROWS), ORACLE_MAX_ROWS)
    rows = run_query(addr, SQL_ACTIVE_SESSIONS, {"row_limit": limit})
    return {"sessions": rows, "count": len(rows)}


def get_blocking_sessions(addr: str, limit: int = ORACLE_MAX_ROWS) -> dict:
    limit = min(int(limit or ORACLE_MAX_ROWS), ORACLE_MAX_ROWS)
    rows = run_query(addr, SQL_BLOCKING_SESSIONS, {"row_limit": limit})
    return {"blocking_chains": rows, "count": len(rows)}


def get_long_running_queries(
    addr: str,
    min_seconds: int = 60,
    limit: int = ORACLE_MAX_ROWS,
) -> dict:
    limit = min(int(limit or ORACLE_MAX_ROWS), ORACLE_MAX_ROWS)
    rows = run_query(addr, SQL_LONG_RUNNING, {"min_seconds": int(min_seconds), "row_limit": limit})
    return {"queries": rows, "count": len(rows)}
