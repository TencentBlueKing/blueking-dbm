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
import logging
import time

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpOracleConnectionException
from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_MAX_ROWS
from backend.dbm_aiagent.mcp_tools.oracle.helpers.oracle_conn import run_queries, run_query
from backend.dbm_aiagent.mcp_tools.oracle.helpers.time_window import local_to_tz, tstz_to_tz

logger = logging.getLogger("root")

SQL_INSTANCE_STATE = f"""
SELECT
    i.instance_name,
    i.host_name,
    i.version,
    {local_to_tz("i.startup_time")} AS startup_time,
    i.status                   AS instance_status,
    i.database_status,
    i.instance_role,
    i.logins,
    i.archiver,
    i.active_state,
    i.blocked,
    d.name                     AS db_name,
    d.database_role,
    d.open_mode,
    d.protection_mode,
    d.protection_level,
    d.switchover_status,
    d.flashback_on,
    d.log_mode
FROM v$instance i, v$database d
"""

SQL_SESSION_COUNTS = """
SELECT
    COUNT(*)                                                    AS total_sessions,
    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END)          AS active_sessions,
    SUM(CASE WHEN blocking_session IS NOT NULL THEN 1 ELSE 0 END) AS blocked_sessions,
    SUM(CASE WHEN type = 'USER' THEN 1 ELSE 0 END)              AS user_sessions
FROM v$session
"""

SQL_SESSION_LIMIT = """
SELECT TO_NUMBER(value) AS session_limit
FROM v$parameter
WHERE name = 'sessions'
"""

# 近 N 分钟告警日志中的 ORA 错误，按错误码（补零为 5 位）聚合，sample_text 取最近一条
SQL_ALERT_LOG_ERRORS = f"""
SELECT * FROM (
    SELECT
        'ORA-' || LPAD(err_no, 5, '0')                        AS error_code,
        COUNT(*)                                              AS occurrences,
        {tstz_to_tz("MIN(ts)")} AS first_seen,
        {tstz_to_tz("MAX(ts)")} AS last_seen,
        MAX(message_text) KEEP (DENSE_RANK LAST ORDER BY ts)  AS sample_text
    FROM (
        SELECT
            originating_timestamp                                         AS ts,
            REGEXP_SUBSTR(message_text, 'ORA-([0-9]{{1,5}})', 1, 1, 'c', 1) AS err_no,
            SUBSTR(message_text, 1, 500)                                  AS message_text
        FROM v$diag_alert_ext
        WHERE originating_timestamp > SYSTIMESTAMP - NUMTODSINTERVAL(:minutes, 'MINUTE')
          AND message_level <= 16
          AND message_text LIKE '%ORA-%'
    )
    WHERE err_no IS NOT NULL
    GROUP BY 'ORA-' || LPAD(err_no, 5, '0')
    ORDER BY occurrences DESC, last_seen DESC
) WHERE ROWNUM <= :row_limit
"""

_HEALTHY_INSTANCE_STATUS = {"OPEN"}
_HEALTHY_DB_STATUS = {"ACTIVE"}


def _derive_health(state: dict, session_usage_pct: float) -> dict:
    """根据各状态字段汇总出一个简单的 health 等级和原因列表。"""
    reasons = []
    level = "healthy"

    inst_status = (state.get("instance_status") or "").upper()
    db_status = (state.get("database_status") or "").upper()
    logins = (state.get("logins") or "").upper()
    archiver = (state.get("archiver") or "").upper()
    blocked = (state.get("blocked") or "").upper()

    if inst_status not in _HEALTHY_INSTANCE_STATUS:
        level = "critical"
        reasons.append(f"instance_status={inst_status}")
    if db_status not in _HEALTHY_DB_STATUS:
        level = "critical"
        reasons.append(f"database_status={db_status}")
    if archiver == "FAILED":
        level = "critical"
        reasons.append("archiver=FAILED")
    if blocked == "YES":
        level = "critical"
        reasons.append("instance blocked")

    if level == "healthy":
        if logins == "RESTRICTED":
            level = "warning"
            reasons.append("logins=RESTRICTED")
        if session_usage_pct >= 90:
            level = "warning" if level == "healthy" else level
            reasons.append(f"session usage {session_usage_pct:.1f}% >= 90%")

    return {"level": level, "reasons": reasons}


def check_instance_status(addr: str) -> dict:
    """综合探活：连通性、实例/数据库状态、会话使用率、DG 角色、探活耗时，并汇总 health 等级。"""
    start_ts = time.monotonic()

    try:
        state_rows, sess_rows, limit_rows = run_queries(
            addr,
            [(SQL_INSTANCE_STATE, None), (SQL_SESSION_COUNTS, None), (SQL_SESSION_LIMIT, None)],
        )
    except DBMMcpOracleConnectionException as e:
        latency_ms = int((time.monotonic() - start_ts) * 1000)
        return {
            "reachable": False,
            "latency_ms": latency_ms,
            "health": {"level": "critical", "reasons": [f"connect failed: {e.message}"]},
            "state": {},
            "sessions": {},
        }

    latency_ms = int((time.monotonic() - start_ts) * 1000)
    state = state_rows[0] if state_rows else {}
    sess = sess_rows[0] if sess_rows else {}
    session_limit = (limit_rows[0].get("session_limit") if limit_rows else 0) or 0

    total_sessions = sess.get("total_sessions") or 0
    session_usage_pct = (total_sessions / session_limit * 100) if session_limit else 0.0
    sess["session_limit"] = session_limit
    sess["session_usage_pct"] = round(session_usage_pct, 2)

    health = _derive_health(state, session_usage_pct)

    return {
        "reachable": True,
        "latency_ms": latency_ms,
        "health": health,
        "state": state,
        "sessions": sess,
    }


def get_alert_log_errors(
    addr: str,
    minutes: int = 120,
    limit: int = ORACLE_MAX_ROWS,
) -> dict:
    """查询近 N 分钟告警日志中的 ORA 错误，按错误码聚合；limit 约束错误码个数。"""
    limit = min(int(limit or ORACLE_MAX_ROWS), ORACLE_MAX_ROWS)
    rows = run_query(addr, SQL_ALERT_LOG_ERRORS, {"minutes": int(minutes), "row_limit": limit})
    return {"errors": rows, "count": len(rows), "minutes": minutes}
