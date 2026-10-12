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

from typing import Dict, List, Tuple

from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpFeatureDisabledException,
    DBMMcpOracleQueryException,
    DBMMcpUnsafeIdentifierException,
)
from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_AWR_MAX_LINES, ORACLE_ENABLE_AWR, ORACLE_MAX_ROWS
from backend.dbm_aiagent.mcp_tools.oracle.enums import OracleAwrFormat
from backend.dbm_aiagent.mcp_tools.oracle.helpers.oracle_conn import run_query
from backend.dbm_aiagent.mcp_tools.oracle.helpers.time_window import local_to_tz, tz_to_local

# 时间入参已由 serializer 规范化为展示时区（默认 +08:00），SQL 内换算为数据库本地时间后与 end_interval_time 比较；
# 出参时间统一按展示时区输出
_BEGIN = tz_to_local("begin_time")
_END = tz_to_local("end_time")

# 列出最近 N 天的 AWR 快照。interval_sec 用于发现采集缺口
SQL_LIST_AWR_SNAPSHOTS = f"""
WITH cur AS (
    SELECT d.dbid AS dbid, i.instance_number AS inst
    FROM   v$database d, v$instance i
)
SELECT * FROM (
    SELECT
        s.snap_id,
        {local_to_tz("s.begin_interval_time")} AS begin_interval_time,
        {local_to_tz("s.end_interval_time")}   AS end_interval_time,
        ROUND((CAST(s.end_interval_time AS DATE) - CAST(s.begin_interval_time AS DATE)) * 86400)
                                               AS interval_sec
    FROM dba_hist_snapshot s, cur c
    WHERE s.dbid = c.dbid AND s.instance_number = c.inst
      AND s.end_interval_time > SYSTIMESTAMP - NUMTODSINTERVAL(:days, 'DAY')
    ORDER BY s.snap_id DESC
) WHERE ROWNUM <= :row_limit
"""

# 把时间区间解析为快照区间，采用「外扩」策略保证覆盖请求区间：
#   begin_snap = end_interval_time <= begin_time 的最大快照
#   end_snap   = end_interval_time >= end_time   的最小快照
SQL_RESOLVE_SNAP_RANGE = f"""
WITH cur AS (
    SELECT d.dbid AS dbid, i.instance_number AS inst
    FROM v$database d, v$instance i
), snaps AS (
    SELECT s.snap_id, s.end_interval_time
    FROM dba_hist_snapshot s, cur c
    WHERE s.dbid = c.dbid AND s.instance_number = c.inst
), before_begin AS (
    SELECT snap_id, end_interval_time FROM snaps WHERE end_interval_time <= {_BEGIN}
), after_end AS (
    SELECT snap_id, end_interval_time FROM snaps WHERE end_interval_time >= {_END}
)
SELECT
    (SELECT MAX(snap_id) FROM before_begin)                                AS begin_snap,
    (SELECT MIN(snap_id) FROM after_end)                                   AS end_snap,
    (SELECT {local_to_tz("MAX(end_interval_time)")} FROM before_begin)     AS actual_begin_time,
    (SELECT {local_to_tz("MIN(end_interval_time)")} FROM after_end)        AS actual_end_time,
    (SELECT MIN(snap_id) FROM snaps)                                       AS oldest_snap,
    (SELECT MAX(snap_id) FROM snaps)                                       AS newest_snap,
    (SELECT {local_to_tz("MIN(end_interval_time)")} FROM snaps)            AS oldest_snap_time,
    (SELECT {local_to_tz("MAX(end_interval_time)")} FROM snaps)            AS newest_snap_time
FROM dual
"""

# AWR 报告（pipelined function，按行返回），固定取当前实例，不支持 RAC
SQL_AWR_REPORT_TMPL = """
SELECT t.output
FROM v$database d, v$instance i,
     TABLE(
         DBMS_WORKLOAD_REPOSITORY.awr_report_{fmt}(
             d.dbid,
             i.instance_number,
             :begin_snap,
             :end_snap,
             0
         )
     ) t
"""


# 取自 dba_hist_sysstat 的累计量：(出参别名, stat_name)
_SYSSTAT_METRICS = (
    ("logical_reads", "session logical reads"),
    ("physical_reads", "physical reads"),
    ("physical_writes", "physical writes"),
    ("redo_size", "redo size"),
    ("user_calls", "user calls"),
    ("executes", "execute count"),
    ("parses", "parse count (total)"),
    ("hard_parses", "parse count (hard)"),
    ("commits", "user commits"),
    ("rollbacks", "user rollbacks"),
)

# 参与 delta 计算的全部累计量（时间模型 + 系统统计）
_DELTA_ALIASES = ("db_time", "db_cpu") + tuple(alias for alias, _ in _SYSSTAT_METRICS)

_SYSSTAT_SUM_COLS = ",\n           ".join(
    f"SUM(CASE WHEN ss.stat_name = '{name}' THEN ss.value END) AS {alias}" for alias, name in _SYSSTAT_METRICS
)
_SYSSTAT_NAME_LIST = ", ".join(f"'{name}'" for _, name in _SYSSTAT_METRICS)
_SYSSTAT_SELECT_COLS = ", ".join(f"st.{alias}" for alias, _ in _SYSSTAT_METRICS)
_LAG_COLS = ",\n           ".join(
    f"{alias} - LAG({alias}) OVER (ORDER BY snap_id) AS d_{alias}" for alias in _DELTA_ALIASES
)

# 按快照逐段求 delta 的负载指标序列，时间模型单位为微秒
SQL_AWR_LOAD_PROFILE = f"""
WITH cur AS (
    SELECT d.dbid AS dbid, i.instance_number AS inst
    FROM   v$database d, v$instance i
), snaps AS (
    SELECT s.snap_id, CAST(s.end_interval_time AS DATE) AS end_dt
    FROM   dba_hist_snapshot s, cur c
    WHERE  s.dbid = c.dbid AND s.instance_number = c.inst
      AND  s.snap_id BETWEEN :begin_snap AND :end_snap
), tm AS (
    SELECT t.snap_id,
           SUM(CASE WHEN t.stat_name = 'DB time' THEN t.value END) AS db_time,
           SUM(CASE WHEN t.stat_name = 'DB CPU'  THEN t.value END) AS db_cpu
    FROM   dba_hist_sys_time_model t, cur c
    WHERE  t.dbid = c.dbid AND t.instance_number = c.inst
      AND  t.snap_id BETWEEN :begin_snap AND :end_snap
      AND  t.stat_name IN ('DB time', 'DB CPU')
    GROUP  BY t.snap_id
), st AS (
    SELECT ss.snap_id,
           {_SYSSTAT_SUM_COLS}
    FROM   dba_hist_sysstat ss, cur c
    WHERE  ss.dbid = c.dbid AND ss.instance_number = c.inst
      AND  ss.snap_id BETWEEN :begin_snap AND :end_snap
      AND  ss.stat_name IN ({_SYSSTAT_NAME_LIST})
    GROUP  BY ss.snap_id
), j AS (
    SELECT s.snap_id, s.end_dt, tm.db_time, tm.db_cpu, {_SYSSTAT_SELECT_COLS}
    FROM   snaps s
    LEFT   JOIN tm ON tm.snap_id = s.snap_id
    LEFT   JOIN st ON st.snap_id = s.snap_id
), d AS (
    SELECT snap_id, end_dt,
           LAG(end_dt) OVER (ORDER BY snap_id) AS prev_dt,
           {_LAG_COLS}
    FROM   j
), e AS (
    SELECT snap_id, prev_dt, end_dt,
           ROUND((end_dt - prev_dt) * 86400) AS interval_sec,
           {", ".join(f"d_{alias}" for alias in _DELTA_ALIASES)}
    FROM   d
    WHERE  prev_dt IS NOT NULL
)
SELECT snap_id,
       {local_to_tz("prev_dt")}                                        AS begin_time,
       {local_to_tz("end_dt")}                                         AS end_time,
       interval_sec,
       ROUND(d_db_time / 1000000, 1)                                   AS db_time_sec,
       ROUND(d_db_cpu / 1000000, 1)                                    AS db_cpu_sec,
       ROUND(d_db_time / 1000000 / NULLIF(interval_sec, 0), 2)         AS aas,
       ROUND(d_db_cpu * 100 / NULLIF(d_db_time, 0), 1)                 AS db_cpu_pct,
       ROUND(d_logical_reads / NULLIF(interval_sec, 0))                AS logical_reads_per_sec,
       ROUND(d_physical_reads / NULLIF(interval_sec, 0))               AS physical_reads_per_sec,
       ROUND(d_physical_writes / NULLIF(interval_sec, 0))              AS physical_writes_per_sec,
       ROUND(d_redo_size / 1048576 / NULLIF(interval_sec, 0), 3)       AS redo_mb_per_sec,
       ROUND(d_executes / NULLIF(interval_sec, 0), 1)                  AS executes_per_sec,
       ROUND(d_user_calls / NULLIF(interval_sec, 0), 1)                AS user_calls_per_sec,
       ROUND((d_commits + d_rollbacks) / NULLIF(interval_sec, 0), 2)   AS transactions_per_sec,
       ROUND(d_parses / NULLIF(interval_sec, 0), 1)                    AS parses_per_sec,
       ROUND(d_hard_parses / NULLIF(interval_sec, 0), 2)               AS hard_parses_per_sec,
       ROUND(d_hard_parses * 100 / NULLIF(d_parses, 0), 2)             AS hard_parse_pct
FROM e
ORDER BY snap_id
"""


def _ensure_enabled():
    if not ORACLE_ENABLE_AWR:
        raise DBMMcpFeatureDisabledException(feature="Oracle AWR")


def list_awr_snapshots(
    addr: str,
    days: int = 7,
    limit: int = ORACLE_MAX_ROWS,
) -> dict:
    _ensure_enabled()
    limit = min(int(limit or ORACLE_MAX_ROWS), ORACLE_MAX_ROWS)
    rows = run_query(addr, SQL_LIST_AWR_SNAPSHOTS, {"days": int(days), "row_limit": limit})
    return {"snapshots": rows, "count": len(rows), "days": days}


def _render_report(addr: str, begin_snap: int, end_snap: int, report_format: str) -> Tuple[str, bool]:
    """生成 AWR 报告并按行拼接，返回 (报告内容, 是否触达行数上限被截断)。"""
    # report_format 会拼入函数名，必须白名单校验
    if report_format not in OracleAwrFormat.get_values():
        raise DBMMcpUnsafeIdentifierException(msg=f"invalid awr report format: {report_format}")

    rows = run_query(
        addr,
        SQL_AWR_REPORT_TMPL.format(fmt=report_format),
        {"begin_snap": int(begin_snap), "end_snap": int(end_snap)},
    )
    content = "\n".join(row["output"] for row in rows if row.get("output") is not None)
    return content, len(rows) >= ORACLE_AWR_MAX_LINES


def _build_result(
    begin_snap: int,
    end_snap: int,
    report_format: str,
    content: str,
    truncated: bool,
    warnings: List[str],
) -> dict:
    if truncated:
        hint = f"报告行数已触达 DRS 上限（{ORACLE_AWR_MAX_LINES} 行），内容被截断，建议缩小快照区间"
        if report_format == OracleAwrFormat.HTML.value:
            hint += "，或改用 text 格式（体积约为 html 的 1/4）"
        warnings = warnings + [hint]
    return {
        "begin_snap": begin_snap,
        "end_snap": end_snap,
        "format": report_format,
        "report": content,
        "report_size": len(content),
        "truncated": truncated,
        "warnings": warnings,
    }


def generate_awr_report(
    addr: str,
    begin_snap: int,
    end_snap: int,
    report_format: str = OracleAwrFormat.TEXT.value,
) -> dict:
    """生成指定快照区间 [begin_snap, end_snap] 的 AWR 报告（当前实例）。"""
    _ensure_enabled()
    content, truncated = _render_report(addr, begin_snap, end_snap, report_format)
    return _build_result(begin_snap, end_snap, report_format, content, truncated, [])


def _resolve_snap_range(addr: str, begin_time: str, end_time: str) -> Tuple[int, int, Dict[str, str], List[str]]:
    """把时间区间外扩解析为快照区间，返回 (begin_snap, end_snap, actual, warnings)。"""
    rows = run_query(addr, SQL_RESOLVE_SNAP_RANGE, {"begin_time": begin_time, "end_time": end_time})
    r = rows[0] if rows else {}

    if r.get("oldest_snap") is None:
        raise DBMMcpOracleQueryException(msg="AWR 仓库中没有任何快照，请确认 AWR 采集已启用")

    warnings: List[str] = []
    begin_snap = r.get("begin_snap")
    end_snap = r.get("end_snap")
    actual_begin_time = r.get("actual_begin_time")
    actual_end_time = r.get("actual_end_time")

    # 请求起点早于最早快照，无法外扩
    if begin_snap is None:
        raise DBMMcpOracleQueryException(
            msg=(
                f"begin_time={begin_time} 早于最早可用快照（snap_id={r.get('oldest_snap')}, "
                f"{r.get('oldest_snap_time')}），已超出 AWR 保留期"
            )
        )

    # 请求终点晚于最新快照，回退到最新快照
    if end_snap is None:
        end_snap = r.get("newest_snap")
        actual_end_time = r.get("newest_snap_time")
        warnings.append(
            f"end_time={end_time} 晚于最新快照，已回退至 snap_id={end_snap}（{actual_end_time}）；" "该时刻之后的活动尚未进入 AWR，如需分析请改用 ASH 工具"
        )

    # 回退后区间内没有完整的快照间隔
    if end_snap <= begin_snap:
        raise DBMMcpOracleQueryException(
            msg=(
                f"[{begin_time}, {end_time}] 区间内尚无完整的快照间隔"
                f"（最新快照 snap_id={end_snap}, {actual_end_time}）。"
                "AWR 报告需要区间两端各有一个快照，请等待下一次快照生成，"
                "或改用 ASH 工具分析最近时段"
            )
        )

    begin_snap, end_snap = int(begin_snap), int(end_snap)
    actual = {
        "actual_begin_snap": begin_snap,
        "actual_end_snap": end_snap,
        "actual_begin_time": actual_begin_time,
        "actual_end_time": actual_end_time,
    }
    return begin_snap, end_snap, actual, warnings


def generate_awr_report_by_time(
    addr: str,
    begin_time: str,
    end_time: str,
    report_format: str = OracleAwrFormat.TEXT.value,
) -> dict:
    """
    按时间区间生成 AWR 报告：先解析为快照区间并校验，再生成报告。
    实际报告区间可能宽于请求区间，由出参 actual_* 回显。
    """
    _ensure_enabled()

    begin_snap, end_snap, actual, warnings = _resolve_snap_range(addr, begin_time, end_time)
    content, truncated = _render_report(addr, begin_snap, end_snap, report_format)

    result = _build_result(begin_snap, end_snap, report_format, content, truncated, warnings)
    result.update(
        {
            "requested_begin_time": begin_time,
            "requested_end_time": end_time,
            **actual,
        }
    )
    return result


def get_awr_load_profile(
    addr: str,
    begin_time: str,
    end_time: str,
) -> dict:
    """按快照逐段输出负载指标序列（dba_hist_sys_time_model + dba_hist_sysstat 的 delta）。

    返回结构化 JSON（通常几 KB），可由模型直接调用，无需裁剪。
    """
    _ensure_enabled()

    begin_snap, end_snap, actual, warnings = _resolve_snap_range(addr, begin_time, end_time)
    rows = run_query(addr, SQL_AWR_LOAD_PROFILE, {"begin_snap": begin_snap, "end_snap": end_snap})

    warnings = list(warnings)
    if not rows:
        warnings.append("区间内没有可用于求差的相邻快照对，无法计算增量指标")

    return {
        "requested_begin_time": begin_time,
        "requested_end_time": end_time,
        **actual,
        "snapshot_count": len(rows),
        "profile": rows,
        "warnings": warnings,
    }
