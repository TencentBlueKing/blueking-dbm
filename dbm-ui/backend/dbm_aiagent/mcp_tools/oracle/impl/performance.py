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

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpFeatureDisabledException,
    DBMMcpOracleQueryException,
    DBMMcpUnsafeIdentifierException,
)
from backend.dbm_aiagent.mcp_tools.oracle.constants import (
    ORACLE_ASH_MAX_LOOKBACK_DAYS,
    ORACLE_ENABLE_AWR,
    ORACLE_MAX_ROWS,
    ORACLE_SQL_TZ_MINUTE_FORMAT,
    ORACLE_XPLAN_MAX_LINES,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.ash_sql import (
    HIST_SQLTEXT,
    SQLSTATS_TEXT,
    top_events_sql,
    top_sql_sql,
    wait_class_sql,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.ash_window import (
    FUTURE_TOLERANCE_SEC,
    compute_aas,
    compute_coverage,
    derive_activity,
    derive_load,
    slim_window,
    to_db_time_sec,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.oracle_conn import run_queries, run_query
from backend.dbm_aiagent.mcp_tools.oracle.helpers.time_window import local_to_tz, tz_to_local

# 时间入参已由 serializer 规范化为展示时区，SQL 内换算为数据库本地时间后与 sample_time / SYSDATE 比较
_BEGIN = tz_to_local("begin_time")
_END = tz_to_local("end_time")

_ASH_TABLE = "v$active_session_history"
_ASH_FILTER = f"h.sample_time BETWEEN {_BEGIN} AND {_END} AND h.session_type = 'FOREGROUND'"

# 内存 ASH 每个样本代表 1 秒 DB time
_ASH_SAMPLE_INTERVAL_SEC = 1

# sql_id 为 13 位 base-32 字符串，限定 ASCII 字母数字
_SQL_ID_RE = re.compile(r"^[A-Za-z0-9_]{1,30}$")

# DBMS_XPLAN 找不到计划时返回的提示文本特征（DISPLAY_CURSOR / DISPLAY_AWR 共用）
_XPLAN_NOT_FOUND_MARKERS = ("cannot be found", "cannot fetch plan", "no plan found")

SQL_PLAN = """
SELECT plan_table_output AS output
FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(:sql_id, :child_number, 'ALL'))
WHERE ROWNUM <= :row_limit
"""

# DISPLAY_AWR 第 2 个参数是 plan_hash_value（为 NULL 时输出全部历史计划），第 3 个 dbid 传 NULL 表示当前库
SQL_PLAN_AWR = """
SELECT plan_table_output AS output
FROM TABLE(DBMS_XPLAN.DISPLAY_AWR(:sql_id, :plan_hash_value, NULL, 'ALL'))
WHERE ROWNUM <= :row_limit
"""

# 该 sql_id 在 AWR 中留存的全部执行计划，用于判断是否发生过计划变更
SQL_PLAN_AWR_HASHES = f"""
SELECT * FROM (
    SELECT p.plan_hash_value,
           {local_to_tz("MIN(p.timestamp)")} AS first_seen,
           {local_to_tz("MAX(p.timestamp)")} AS last_seen
    FROM   dba_hist_sql_plan p
    WHERE  p.sql_id = :sql_id
    GROUP  BY p.plan_hash_value
    ORDER  BY MAX(p.timestamp) DESC
) WHERE ROWNUM <= :row_limit
"""

# 窗口探测：实际统计区间、覆盖率、整体/CPU 样本数、峰值分钟。
# actual_begin = max(请求起点, ASH 最早样本)，actual_end = min(请求终点, SYSDATE)
# SQL 内勿写 -- 注释（下游可能折叠换行）
SQL_ASH_WINDOW = f"""
WITH w AS (
    SELECT {_BEGIN}                 AS req_begin,
           {_END}                   AS req_end,
           SYSDATE                  AS db_now,
           LEAST({_END}, SYSDATE)   AS capped_end
    FROM   dual
), buf AS (
    SELECT MIN(sample_time) AS oldest_sample_time,
           MAX(sample_time) AS latest_sample_time
    FROM   {_ASH_TABLE}
), o AS (
    SELECT COUNT(*)                                               AS total_samples,
           COUNT(CASE WHEN h.session_state = 'ON CPU' THEN 1 END) AS cpu_samples
    FROM   {_ASH_TABLE} h
    WHERE  {_ASH_FILTER}
), pm AS (
    SELECT TRUNC(CAST(h.sample_time AS DATE), 'MI') AS minute, COUNT(*) AS cnt
    FROM   {_ASH_TABLE} h
    WHERE  {_ASH_FILTER}
    GROUP  BY TRUNC(CAST(h.sample_time AS DATE), 'MI')
), peak AS (
    SELECT MAX(cnt)                                              AS peak_minute_samples,
           MAX(minute) KEEP (DENSE_RANK FIRST ORDER BY cnt DESC) AS peak_minute
    FROM   pm
), a AS (
    SELECT GREATEST(w.req_begin,
                    NVL(CAST(f.oldest_sample_time AS DATE), w.req_begin)) AS actual_begin
    FROM   w CROSS JOIN buf f
)
SELECT
    {local_to_tz("w.db_now")}                                             AS db_now,
    {local_to_tz("f.oldest_sample_time")}                                 AS oldest_sample_time,
    {local_to_tz("f.latest_sample_time")}                                 AS latest_sample_time,
    {local_to_tz("a.actual_begin")}                                       AS actual_begin,
    {local_to_tz("w.capped_end")}                                         AS actual_end,
    GREATEST(ROUND((w.capped_end - w.req_begin) * 86400), 0)              AS requested_sec,
    GREATEST(ROUND((w.capped_end - a.actual_begin) * 86400), 0)           AS effective_sec,
    ROUND((w.db_now - w.req_begin) * 86400)                               AS lookback_sec,
    ROUND((w.req_end - w.capped_end) * 86400)                             AS future_sec,
    o.total_samples                                                       AS total_samples,
    o.cpu_samples                                                         AS cpu_samples,
    p.peak_minute_samples,
    {local_to_tz("p.peak_minute", ORACLE_SQL_TZ_MINUTE_FORMAT)}           AS peak_minute,
    (SELECT TO_NUMBER(value) FROM v$parameter WHERE name = 'cpu_count')   AS cpu_count
FROM o CROSS JOIN peak p CROSS JOIN w CROSS JOIN a CROSS JOIN buf f
"""

SQL_ASH_WAIT_CLASS = wait_class_sql(_ASH_TABLE, _ASH_FILTER, _ASH_SAMPLE_INTERVAL_SEC)
SQL_ASH_TOP_EVENTS = top_events_sql(_ASH_TABLE, _ASH_FILTER, _ASH_SAMPLE_INTERVAL_SEC)
SQL_ASH_TOP_SQL = top_sql_sql(
    _ASH_TABLE,
    _ASH_FILTER,
    _ASH_SAMPLE_INTERVAL_SEC,
    # 共享池优先：实时场景下 v$sqlstats 必然比 AWR 新
    sql_text_sources=[SQLSTATS_TEXT, HIST_SQLTEXT],
    with_child_number=True,
)


def _assert_sql_id(sql_id: str) -> None:
    """sql_id 会拼入 DBMS_XPLAN 调用，必须白名单校验。"""
    if not sql_id or not _SQL_ID_RE.match(sql_id):
        raise DBMMcpUnsafeIdentifierException(msg=f"invalid sql_id: {sql_id}")


def _join_plan_text(rows: List[Dict[str, Any]]) -> Tuple[str, bool]:
    """拼接 DBMS_XPLAN 的按行输出，并判断是否取到了计划。"""
    text = "\n".join(row["output"] for row in rows if row.get("output") is not None)
    lowered = text.lower()
    found = bool(text.strip()) and not any(marker in lowered for marker in _XPLAN_NOT_FOUND_MARKERS)
    return text, found


def get_sql_plan(addr: str, sql_id: str, child_number: Optional[int] = None) -> dict:
    """查询 sql_id 的当前执行计划（DISPLAY_CURSOR），child_number 为 None 时输出全部子游标。"""
    _assert_sql_id(sql_id)

    rows = run_query(
        addr,
        SQL_PLAN,
        {
            "sql_id": sql_id,
            "child_number": int(child_number) if child_number is not None else None,
            "row_limit": ORACLE_XPLAN_MAX_LINES,
        },
    )
    plan_text, found = _join_plan_text(rows)

    warnings = []
    if not found:
        warnings.append(f"sql_id={sql_id} 的游标不在共享池中，无法从内存获取执行计划；历史时段请改用 get_sql_plan_awr")
    if len(rows) >= ORACLE_XPLAN_MAX_LINES:
        warnings.append(f"计划文本已达行数上限（{ORACLE_XPLAN_MAX_LINES} 行）被截断，建议指定 child_number 缩小输出")

    return {
        "sql_id": sql_id,
        "found": found,
        "plan_text": plan_text,
        "line_count": len(rows),
        "warnings": warnings,
    }


def get_sql_plan_awr(addr: str, sql_id: str, plan_hash_value: Optional[int] = None) -> dict:
    """查询 sql_id 的历史执行计划（DISPLAY_AWR，读 dba_hist_sql_plan），不依赖共享池。

    定位维度是 plan_hash_value：子游标是内存概念，历史快照中不存在。
    """
    _assert_sql_id(sql_id)

    plan_rows, hash_rows = run_queries(
        addr,
        [
            (
                SQL_PLAN_AWR,
                {
                    "sql_id": sql_id,
                    "plan_hash_value": int(plan_hash_value) if plan_hash_value is not None else None,
                    "row_limit": ORACLE_XPLAN_MAX_LINES,
                },
            ),
            (SQL_PLAN_AWR_HASHES, {"sql_id": sql_id, "row_limit": ORACLE_MAX_ROWS}),
        ],
    )
    plan_text, found = _join_plan_text(plan_rows)
    plan_hash_values = [row.get("plan_hash_value") for row in hash_rows]

    warnings = []
    if not found:
        if plan_hash_values:
            warnings.append(f"plan_hash_value={plan_hash_value} 不在该 sql_id 的 AWR 计划 {plan_hash_values} 中")
        else:
            warnings.append(f"sql_id={sql_id} 不在 dba_hist_sql_plan 中：未被 AWR 采集，或已超出保留期")
    if len(plan_rows) >= ORACLE_XPLAN_MAX_LINES:
        warnings.append(f"计划文本已达行数上限（{ORACLE_XPLAN_MAX_LINES} 行）被截断，建议指定 plan_hash_value 缩小输出")

    return {
        "sql_id": sql_id,
        "plan_hash_value": plan_hash_value,
        "found": found,
        "plan_text": plan_text,
        "line_count": len(plan_rows),
        "plan_hash_values": plan_hash_values,
        "plans": hash_rows,
        "warnings": warnings,
    }


def _assert_within_lookback(w: Dict[str, Any], begin_time: str) -> None:
    """按数据库 SYSDATE 校验请求起点未超出内存 ASH 回溯上限。"""
    lookback_sec = w.get("lookback_sec")
    if lookback_sec is not None and int(lookback_sec) > ORACLE_ASH_MAX_LOOKBACK_DAYS * 86400:
        raise DBMMcpOracleQueryException(
            msg=(
                f"begin_time={begin_time} 距当前数据库时间 {w.get('db_now')} 已超过 "
                f"{ORACLE_ASH_MAX_LOOKBACK_DAYS} 天，超出内存 ASH 的回溯上限；请改用 get_ash_history_* 系列工具"
            )
        )


def _build_ash_window(w: Dict[str, Any], begin_time: str, end_time: str) -> Dict[str, Any]:
    """由窗口探测结果拼装 window 出参。"""
    requested_sec = int(w.get("requested_sec") or 0)
    effective_sec = int(w.get("effective_sec") or 0)
    future_sec = int(w.get("future_sec") or 0)
    total_samples = int(w.get("total_samples") or 0)
    total_db_time = to_db_time_sec(total_samples, _ASH_SAMPLE_INTERVAL_SEC)
    cpu_db_time = to_db_time_sec(w.get("cpu_samples"), _ASH_SAMPLE_INTERVAL_SEC)
    total_aas = compute_aas(total_db_time, effective_sec)
    coverage = compute_coverage(requested_sec, effective_sec)

    warnings: List[str] = []
    if not coverage["coverage_sufficient"]:
        warnings.append(
            f"内存 ASH 仅覆盖请求窗口的 {coverage['coverage_pct']}%（最早样本 {w.get('oldest_sample_time')}），"
            f"低于 {coverage['min_coverage_pct']}% 的可信下限；缓冲区已循环覆盖，请改用 get_ash_history_*"
        )
    if future_sec > FUTURE_TOLERANCE_SEC:
        warnings.append(
            f"end_time={end_time} 晚于当前数据库时间 {w.get('db_now')}，"
            f"窗口尾部 {future_sec} 秒尚未发生，统计区间已收敛至 {w.get('actual_end')}"
        )

    return {
        "requested_begin_time": begin_time,
        "requested_end_time": end_time,
        "db_now": w.get("db_now"),
        "actual_begin": w.get("actual_begin"),
        "actual_end": w.get("actual_end"),
        "oldest_sample_time": w.get("oldest_sample_time"),
        "latest_sample_time": w.get("latest_sample_time"),
        "requested_sec": requested_sec,
        "effective_sec": effective_sec,
        "sample_interval_sec": _ASH_SAMPLE_INTERVAL_SEC,
        "total_samples": total_samples,
        **coverage,
        "total_db_time_sec": total_db_time,
        "total_aas": total_aas,
        "cpu_db_time_sec": cpu_db_time,
        "load": derive_load(total_aas, compute_aas(cpu_db_time, effective_sec), w.get("cpu_count")),
        "activity": derive_activity(
            total_aas,
            total_samples,
            w.get("peak_minute_samples"),
            w.get("peak_minute"),
            w.get("actual_begin"),
            w.get("actual_end"),
            sample_interval_sec=_ASH_SAMPLE_INTERVAL_SEC,
        ),
        "warnings": warnings,
    }


def _run_ash(
    addr: str,
    begin_time: str,
    end_time: str,
    sql: str,
    binds: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """一次 DRS 调用内执行「窗口探测 + ASH 聚合」，按实际覆盖秒数计算 aas。"""
    if not ORACLE_ENABLE_AWR:
        raise DBMMcpFeatureDisabledException(feature="Oracle ASH (Diagnostics Pack, ORACLE_ENABLE_AWR)")

    time_binds = {"begin_time": begin_time, "end_time": end_time}
    window_rows, rows = run_queries(
        addr,
        [(SQL_ASH_WINDOW, time_binds), (sql, {**(binds or {}), **time_binds})],
    )
    w = window_rows[0] if window_rows else {}
    _assert_within_lookback(w, begin_time)

    window = _build_ash_window(w, begin_time, end_time)
    for row in rows:
        row["aas"] = compute_aas(row.get("db_time_sec"), window["effective_sec"])
    return window, rows


def get_ash_wait_class(addr: str, begin_time: str, end_time: str) -> dict:
    """时间窗口内前台会话 DB time 按 wait_class 汇总。"""
    window, rows = _run_ash(addr, begin_time, end_time, SQL_ASH_WAIT_CLASS)
    return {"window": window, "wait_classes": rows, "count": len(rows)}


def get_ash_top_events(addr: str, begin_time: str, end_time: str, limit: int = 20) -> dict:
    """时间窗口内前台会话 Top 等待事件。"""
    limit = min(int(limit or 20), ORACLE_MAX_ROWS)
    window, rows = _run_ash(addr, begin_time, end_time, SQL_ASH_TOP_EVENTS, {"row_limit": limit})
    return {"window": slim_window(window), "events": rows, "count": len(rows)}


def get_ash_top_sql(addr: str, begin_time: str, end_time: str, limit: int = 15) -> dict:
    """时间窗口内前台会话 Top SQL（按 DB time）。"""
    limit = min(int(limit or 15), ORACLE_MAX_ROWS)
    window, rows = _run_ash(addr, begin_time, end_time, SQL_ASH_TOP_SQL, {"row_limit": limit})
    return {"window": slim_window(window), "top_sql": rows, "count": len(rows)}
