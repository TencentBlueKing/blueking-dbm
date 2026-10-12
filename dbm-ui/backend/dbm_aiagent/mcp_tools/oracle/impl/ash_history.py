# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

历史 ASH 分析（dba_hist_active_sess_history）。

与内存 ASH 的三处口径差异：

1. 一个磁盘样本代表约 10 秒 DB time（内存 ASH 为 1 秒），DB time 与 AAS 须按倍率换算；
   sample_sufficient 仍按原始样本数判定。
2. 底层 WRH$_ACTIVE_SESSION_HISTORY 按 (dbid, snap_id) 范围分区，只按 sample_time 过滤会扫描
   全部历史分区，故先把时间区间解析为 snap_id 区间再带入 SQL。
3. 窗口终点是最新快照时刻而非 SYSDATE：视图不含尚未随快照落盘的样本，缺口由 unflushed_sec 给出。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpFeatureDisabledException, DBMMcpOracleQueryException
from backend.dbm_aiagent.mcp_tools.oracle.constants import (
    ORACLE_ASH_TIMELINE_BUCKET_CHOICES,
    ORACLE_ENABLE_AWR,
    ORACLE_HIST_ASH_SAMPLE_INTERVAL_SEC,
    ORACLE_MAX_ROWS,
    ORACLE_SQL_TZ_MINUTE_FORMAT,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.ash_sql import (
    HIST_SQLTEXT,
    SQLSTATS_TEXT,
    top_events_sql,
    top_sql_sql,
    wait_class_sql,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.ash_window import (
    compute_aas,
    compute_coverage,
    derive_activity,
    derive_load,
    slim_window,
    to_db_time_sec,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.oracle_conn import run_queries, run_query
from backend.dbm_aiagent.mcp_tools.oracle.helpers.time_window import local_to_tz, tz_to_local

_BEGIN = tz_to_local("begin_time")
_END = tz_to_local("end_time")

_INTERVAL = ORACLE_HIST_ASH_SAMPLE_INTERVAL_SEC
_TABLE = "dba_hist_active_sess_history"

# dbid + instance_number 过滤避免 DG 切换历史与同机多实例混入；snap_id 区间用于分区裁剪；
# sample_time 做精确过滤（snap 区间必然宽于请求区间）
_FILTER = f"""h.dbid = :dbid
      AND h.instance_number = :instance_number
      AND h.snap_id BETWEEN :snap_lo AND :snap_hi
      AND h.session_type = 'FOREGROUND'
      AND h.sample_time BETWEEN {_BEGIN} AND {_END}"""

# 活跃度判定的峰值桶粒度：10 秒一个样本，1 分钟桶最多 6 个样本、抖动过大
_PEAK_BUCKET_MINUTES = 5
_PEAK_BUCKET_SEC = _PEAK_BUCKET_MINUTES * 60


def _bucket_expr(bucket_minutes: int) -> str:
    """按 bucket_minutes 分桶，桶边界从请求起点（取整到分钟）对齐。

    bucket_minutes 以字面量插入 SQL，调用前必须经白名单校验。
    """
    anchor = f"TRUNC({_BEGIN}, 'MI')"
    return (
        f"({anchor} + FLOOR((CAST(h.sample_time AS DATE) - {anchor}) * 1440 / {bucket_minutes})"
        f" * {bucket_minutes} / 1440)"
    )


# 时间区间 -> snap_id 区间与窗口边界。
# snap_lo 取 end_interval_time >= begin_time 的最小快照：区间内任一样本所属快照的 end_interval_time
# 必然 >= 该样本时刻 >= begin_time，故是不漏样本的下界。snap_hi 同理，缺省时回退最新快照。
# SQL 内勿写 -- 注释（下游可能折叠换行）
SQL_HIST_WINDOW = f"""
WITH cur AS (
    SELECT d.dbid AS dbid, i.instance_number AS inst
    FROM   v$database d, v$instance i
), snaps AS (
    SELECT s.snap_id, s.begin_interval_time, s.end_interval_time
    FROM   dba_hist_snapshot s, cur c
    WHERE  s.dbid = c.dbid AND s.instance_number = c.inst
), bnd AS (
    SELECT MIN(CAST(begin_interval_time AS DATE)) AS oldest_begin,
           MAX(CAST(end_interval_time AS DATE))   AS newest_end,
           MIN(snap_id)                           AS oldest_snap,
           MAX(snap_id)                           AS newest_snap
    FROM   snaps
), w AS (
    SELECT {_BEGIN}                           AS req_begin,
           {_END}                             AS req_end,
           LEAST({_END}, b.newest_end)        AS capped_end,
           GREATEST({_BEGIN}, b.oldest_begin) AS capped_begin,
           b.oldest_begin, b.newest_end, b.oldest_snap, b.newest_snap
    FROM   bnd b
)
SELECT
    (SELECT dbid FROM cur)                                                 AS dbid,
    (SELECT inst FROM cur)                                                 AS instance_number,
    {local_to_tz("SYSDATE")}                                               AS db_now,
    (SELECT MIN(snap_id) FROM snaps WHERE end_interval_time >= {_BEGIN})   AS snap_lo,
    (SELECT MIN(snap_id) FROM snaps WHERE end_interval_time >= {_END})     AS snap_hi,
    w.oldest_snap,
    w.newest_snap,
    {local_to_tz("w.oldest_begin")}                                        AS oldest_snap_time,
    {local_to_tz("w.newest_end")}                                          AS newest_snap_time,
    {local_to_tz("w.capped_begin")}                                        AS actual_begin,
    {local_to_tz("w.capped_end")}                                          AS actual_end,
    GREATEST(ROUND((w.capped_end - w.req_begin) * 86400), 0)               AS requested_sec,
    GREATEST(ROUND((w.capped_end - w.capped_begin) * 86400), 0)            AS effective_sec,
    GREATEST(ROUND((w.req_end - w.capped_end) * 86400), 0)                 AS unflushed_sec,
    (SELECT EXTRACT(HOUR FROM r.snap_interval) * 60
          + EXTRACT(MINUTE FROM r.snap_interval) FROM dba_hist_wr_control r
      WHERE r.dbid = (SELECT dbid FROM cur))                               AS snap_interval_min
FROM w
"""

# 窗口内样本总量、CPU 分量、实际样本首尾、峰值桶
SQL_HIST_PROBE = f"""
WITH o AS (
    SELECT COUNT(*)                                               AS total_samples,
           COUNT(CASE WHEN h.session_state = 'ON CPU' THEN 1 END) AS cpu_samples,
           MIN(h.sample_time)                                     AS first_sample_time,
           MAX(h.sample_time)                                     AS last_sample_time
    FROM   {_TABLE} h
    WHERE  {_FILTER}
), pb AS (
    SELECT {_bucket_expr(_PEAK_BUCKET_MINUTES)} AS bucket, COUNT(*) AS cnt
    FROM   {_TABLE} h
    WHERE  {_FILTER}
    GROUP  BY {_bucket_expr(_PEAK_BUCKET_MINUTES)}
), peak AS (
    SELECT MAX(cnt)                                              AS peak_samples,
           MAX(bucket) KEEP (DENSE_RANK FIRST ORDER BY cnt DESC) AS peak_bucket
    FROM   pb
)
SELECT o.total_samples,
       o.cpu_samples,
       {local_to_tz("o.first_sample_time")}                                AS first_sample_time,
       {local_to_tz("o.last_sample_time")}                                 AS last_sample_time,
       p.peak_samples,
       {local_to_tz("p.peak_bucket", ORACLE_SQL_TZ_MINUTE_FORMAT)}         AS peak_bucket,
       (SELECT TO_NUMBER(value) FROM v$parameter WHERE name = 'cpu_count') AS cpu_count
FROM o CROSS JOIN peak p
"""

SQL_HIST_WAIT_CLASS = wait_class_sql(_TABLE, _FILTER, _INTERVAL)
SQL_HIST_TOP_EVENTS = top_events_sql(_TABLE, _FILTER, _INTERVAL)
SQL_HIST_TOP_SQL = top_sql_sql(
    _TABLE,
    _FILTER,
    _INTERVAL,
    # AWR 优先：历史场景下共享池可能已不含该 SQL
    sql_text_sources=[HIST_SQLTEXT, SQLSTATS_TEXT],
)


def _timeline_sql(bucket_minutes: int) -> str:
    """按桶输出 AAS 曲线。aas 按桶长计算（与窗口整体口径不同），故在 SQL 内算好。"""
    bucket = _bucket_expr(bucket_minutes)
    bucket_sec = bucket_minutes * 60
    return f"""
WITH b AS (
    SELECT {bucket} AS bucket,
           CASE WHEN h.session_state = 'ON CPU' THEN 'CPU' ELSE h.wait_class END AS wait_class
    FROM   {_TABLE} h
    WHERE  {_FILTER}
), per_class AS (
    SELECT bucket, wait_class, COUNT(*) AS cnt
    FROM   b
    GROUP  BY bucket, wait_class
), agg AS (
    SELECT bucket,
           SUM(cnt)                                                              AS samples,
           SUM(CASE WHEN wait_class = 'CPU' THEN cnt ELSE 0 END)                 AS cpu_samples,
           MAX(wait_class) KEEP (DENSE_RANK FIRST ORDER BY cnt DESC, wait_class) AS top_wait_class,
           MAX(cnt) KEEP (DENSE_RANK FIRST ORDER BY cnt DESC, wait_class)        AS top_wait_samples
    FROM   per_class
    GROUP  BY bucket
)
SELECT * FROM (
    SELECT {local_to_tz("a.bucket", ORACLE_SQL_TZ_MINUTE_FORMAT)}      AS bucket_begin,
           a.samples,
           a.samples * {_INTERVAL}                                     AS db_time_sec,
           ROUND(a.samples * {_INTERVAL} / {bucket_sec}, 2)            AS aas,
           ROUND(a.cpu_samples * {_INTERVAL} / {bucket_sec}, 2)        AS aas_cpu,
           a.top_wait_class,
           ROUND(a.top_wait_samples * 100 / a.samples, 1)              AS top_wait_pct
    FROM   agg a
    ORDER  BY a.bucket
) WHERE ROWNUM <= :row_limit
"""


def _ensure_enabled() -> None:
    if not ORACLE_ENABLE_AWR:
        raise DBMMcpFeatureDisabledException(feature="Oracle 历史 ASH (Diagnostics Pack, ORACLE_ENABLE_AWR)")


def _resolve_window(addr: str, begin_time: str, end_time: str) -> Dict[str, Any]:
    """解析 snap_id 区间与窗口边界；区间不可用时直接报错，避免白跑聚合查询。"""
    rows = run_query(addr, SQL_HIST_WINDOW, {"begin_time": begin_time, "end_time": end_time})
    w = rows[0] if rows else {}

    if w.get("oldest_snap") is None:
        raise DBMMcpOracleQueryException(msg="AWR 仓库中没有任何快照，历史 ASH 不可用，请确认 AWR 采集已启用")

    # snap_lo 为空说明请求起点晚于所有快照，snap_hi 为空说明请求终点晚于最新快照，分别回退到边界
    w["dbid"] = int(w["dbid"])
    w["instance_number"] = int(w["instance_number"])
    w["snap_lo"] = int(w.get("snap_lo") or w["oldest_snap"])
    w["snap_hi"] = int(w.get("snap_hi") or w["newest_snap"])
    if w["snap_hi"] < w["snap_lo"]:
        raise DBMMcpOracleQueryException(
            msg=(
                f"[{begin_time}, {end_time}] 区间内没有已落盘的 AWR 快照"
                f"（最新快照时刻 {w.get('newest_snap_time')}）；该时段的 ASH 样本尚未写入磁盘，"
                "请改用内存 ASH 工具（get_ash_wait_class 等）"
            )
        )
    return w


def _build_window(w: Dict[str, Any], probe: Dict[str, Any], begin_time: str, end_time: str) -> Dict[str, Any]:
    """拼装 window 出参，字段与内存 ASH 对齐以便两条链路衔接。"""
    requested_sec = int(w.get("requested_sec") or 0)
    effective_sec = int(w.get("effective_sec") or 0)
    unflushed_sec = int(w.get("unflushed_sec") or 0)
    total_samples = int(probe.get("total_samples") or 0)
    total_db_time = to_db_time_sec(total_samples, _INTERVAL)
    cpu_db_time = to_db_time_sec(probe.get("cpu_samples"), _INTERVAL)
    total_aas = compute_aas(total_db_time, effective_sec)
    coverage = compute_coverage(requested_sec, effective_sec)

    warnings: List[str] = []
    if not coverage["coverage_sufficient"]:
        warnings.append(
            f"历史 ASH 仅覆盖请求窗口的 {coverage['coverage_pct']}%（最早快照 {w.get('oldest_snap_time')}），"
            f"低于 {coverage['min_coverage_pct']}% 的可信下限，请求起点早于 AWR 保留期"
        )
    if unflushed_sec > 0:
        warnings.append(
            f"end_time={end_time} 晚于最新快照 {w.get('newest_snap_time')}，"
            f"尾部 {unflushed_sec} 秒的样本尚未落盘，统计区间已收敛；该段请改用内存 ASH 工具"
        )

    return {
        "requested_begin_time": begin_time,
        "requested_end_time": end_time,
        "db_now": w.get("db_now"),
        "actual_begin": w.get("actual_begin"),
        "actual_end": w.get("actual_end"),
        "first_sample_time": probe.get("first_sample_time"),
        "last_sample_time": probe.get("last_sample_time"),
        "oldest_snap_time": w.get("oldest_snap_time"),
        "newest_snap_time": w.get("newest_snap_time"),
        "snap_lo": w.get("snap_lo"),
        "snap_hi": w.get("snap_hi"),
        "snap_interval_min": w.get("snap_interval_min"),
        "requested_sec": requested_sec,
        "effective_sec": effective_sec,
        "unflushed_sec": unflushed_sec,
        "sample_interval_sec": _INTERVAL,
        "total_samples": total_samples,
        **coverage,
        "total_db_time_sec": total_db_time,
        "total_aas": total_aas,
        "cpu_db_time_sec": cpu_db_time,
        "load": derive_load(total_aas, compute_aas(cpu_db_time, effective_sec), probe.get("cpu_count")),
        "activity": derive_activity(
            total_aas,
            total_samples,
            probe.get("peak_samples"),
            probe.get("peak_bucket"),
            w.get("actual_begin"),
            w.get("actual_end"),
            sample_interval_sec=_INTERVAL,
            peak_bucket_sec=_PEAK_BUCKET_SEC,
            peak_field="peak_bucket",
        ),
        "warnings": warnings,
    }


def _run(
    addr: str,
    begin_time: str,
    end_time: str,
    sql: str,
    binds: Optional[Dict[str, Any]] = None,
    row_aas: bool = True,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """执行历史 ASH 查询。

    分两次 DRS 调用：先解析 snap 区间（只查 dba_hist_snapshot，很轻），再带着 snap_id 字面量
    做窗口探测与聚合，以确保分区裁剪静态生效。
    """
    _ensure_enabled()

    w = _resolve_window(addr, begin_time, end_time)
    scope = {
        "begin_time": begin_time,
        "end_time": end_time,
        "dbid": w["dbid"],
        "instance_number": w["instance_number"],
        "snap_lo": w["snap_lo"],
        "snap_hi": w["snap_hi"],
    }

    probe_rows, rows = run_queries(addr, [(SQL_HIST_PROBE, scope), (sql, {**(binds or {}), **scope})])
    window = _build_window(w, probe_rows[0] if probe_rows else {}, begin_time, end_time)
    if row_aas:
        for row in rows:
            row["aas"] = compute_aas(row.get("db_time_sec"), window["effective_sec"])
    return window, rows


def pick_bucket_minutes(span_sec: int, bucket_minutes: Optional[int] = None) -> int:
    """选择分桶粒度：显式指定时校验行数不超限，否则自动选最细且不超限的粒度。"""
    span_min = max(int(span_sec) // 60, 1)
    if bucket_minutes:
        bucket_minutes = int(bucket_minutes)
        if bucket_minutes not in ORACLE_ASH_TIMELINE_BUCKET_CHOICES:
            raise DBMMcpOracleQueryException(
                msg=f"bucket_minutes 只能取 {list(ORACLE_ASH_TIMELINE_BUCKET_CHOICES)}，收到 {bucket_minutes}"
            )
        if span_min / bucket_minutes > ORACLE_MAX_ROWS:
            raise DBMMcpOracleQueryException(
                msg=(
                    f"按 {bucket_minutes} 分钟分桶会产生约 {int(span_min / bucket_minutes)} 行，"
                    f"超过返回上限 {ORACLE_MAX_ROWS}；请调大 bucket_minutes 或缩小时间窗口"
                )
            )
        return bucket_minutes

    for choice in ORACLE_ASH_TIMELINE_BUCKET_CHOICES:
        if span_min / choice <= ORACLE_MAX_ROWS:
            return choice
    return ORACLE_ASH_TIMELINE_BUCKET_CHOICES[-1]


def get_ash_history_timeline(
    addr: str,
    begin_time: str,
    end_time: str,
    bucket_minutes: Optional[int] = None,
) -> dict:
    """历史时段的 AAS 时间曲线，用于定位被区间平均值掩盖的尖峰。"""
    _ensure_enabled()

    # 入参已由 serializer 规范化为带偏移的 ISO 8601，本地换算跨度即可，无需数据库往返
    span_sec = int((datetime.fromisoformat(end_time) - datetime.fromisoformat(begin_time)).total_seconds())
    bucket = pick_bucket_minutes(span_sec, bucket_minutes)

    window, rows = _run(
        addr,
        begin_time,
        end_time,
        _timeline_sql(bucket),
        {"row_limit": ORACLE_MAX_ROWS},
        row_aas=False,
    )

    warnings = list(window["warnings"])
    if len(rows) >= ORACLE_MAX_ROWS:
        warnings.append(f"曲线已达返回行数上限（{ORACLE_MAX_ROWS} 行）被截断，请调大 bucket_minutes 或缩小窗口")

    expected = int(window["effective_sec"] // (bucket * 60)) if window["effective_sec"] else 0
    slim = slim_window(window)
    slim.update(
        {
            "bucket_minutes": bucket,
            "bucket_count": len(rows),
            # 两者之差即无活跃样本的空闲桶数（空桶不出现在序列中）
            "expected_bucket_count": expected,
            "total_aas": window["total_aas"],
            "warnings": warnings,
        }
    )
    return {"window": slim, "timeline": rows, "count": len(rows)}


def get_ash_history_wait_class(addr: str, begin_time: str, end_time: str) -> dict:
    """历史时段内前台会话 DB time 按 wait_class 汇总，含 load / activity 分级。"""
    window, rows = _run(addr, begin_time, end_time, SQL_HIST_WAIT_CLASS)
    return {"window": window, "wait_classes": rows, "count": len(rows)}


def get_ash_history_top_events(addr: str, begin_time: str, end_time: str, limit: int = 20) -> dict:
    """历史时段内前台会话 Top 等待事件。"""
    limit = min(int(limit or 20), ORACLE_MAX_ROWS)
    window, rows = _run(addr, begin_time, end_time, SQL_HIST_TOP_EVENTS, {"row_limit": limit})
    return {"window": slim_window(window), "events": rows, "count": len(rows)}


def get_ash_history_top_sql(addr: str, begin_time: str, end_time: str, limit: int = 15) -> dict:
    """历史时段内前台会话 Top SQL（按 DB time）。"""
    limit = min(int(limit or 15), ORACLE_MAX_ROWS)
    window, rows = _run(addr, begin_time, end_time, SQL_HIST_TOP_SQL, {"row_limit": limit})
    return {"window": slim_window(window), "top_sql": rows, "count": len(rows)}
