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
import copy
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend import env
from backend.components import BKMonitorV3Api
from backend.utils.time import timezone2timestamp

logger = logging.getLogger("root")

UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 3,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    "start_time": 1697100405,
    "end_time": 1697101305,
    "slimit": 500,
    "down_sample_range": "1m",
    "type": "range",
    "step": "auto",
}


# 可选实例过滤：传入 instance_host 时追加到 PromQL 的 label 中
def _instance_filter(instance_host: Optional[str]) -> str:
    if instance_host and instance_host.strip():
        return f',bk_target_ip="{instance_host.strip()}"'
    return ""


# 所有 series 的 datapoints 总数超过此值时，在返回结果中增加 reminder 提醒字段
EXTRACT_SERIES_STATS_DATAPOINTS_LIMIT = 6400

# 查询结束时间早于当前时间超过此天数且无数据时，在结果中提示可能因保留策略导致无数据
PAST_RANGE_HINT_DAYS = 7


def _extract_series_stats(datapoints: List[List]) -> Dict[str, Any]:
    """
    从 datapoints [[value, timestamp], ...] 计算 min, max, avg, max_time, null_count。
    value 可为 int/float 或 None。
    """
    values_ts: List[Tuple[float, float]] = []
    null_count = 0
    for point in datapoints or []:
        if len(point) >= 2:
            val, ts = point[0], float(point[1])
            if val is None:
                null_count += 1
            else:
                try:
                    fval = float(val)
                    values_ts.append((fval, ts))
                except (TypeError, ValueError):
                    null_count += 1
        else:
            null_count += 1

    if not values_ts:
        return {
            "min": None,
            "max": None,
            "avg": None,
            "max_time": None,
            "null_count": null_count,
        }

    values = [v for v, _ in values_ts]
    min_val = min(values)
    max_val = max(values)
    avg_val = sum(values) / len(values)
    # max_time: timestamp at which max value occurs (first occurrence)
    max_time = next(ts for v, ts in values_ts if v == max_val)
    return {
        "min": min_val,
        "max": max_val,
        "avg": round(avg_val, 6),
        "max_time": max_time,
        "null_count": null_count,
    }


def _add_total_series_and_stats(
    series: List[Dict[str, Any]],
    n: int = EXTRACT_SERIES_STATS_DATAPOINTS_LIMIT,
    start_time: Any = None,
    end_time: Any = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    为每个 series 增加 min/max/avg/max_time/null_count，并追加一个 total 系列（所有 series 按时间戳求和）。
    若所有 series 的 datapoints 总数超过 n（默认 6400），返回的 reminder 为提醒文案，否则为 None。
    """
    if not series:
        return [], None

    # 按时间戳汇总所有 series 的值 -> total datapoints
    ts_to_sum: Dict[float, float] = {}
    for s in series:
        for point in s.get("datapoints") or []:
            if len(point) >= 2:
                val, ts = point[0], float(point[1])
                if val is not None:
                    try:
                        ts_to_sum[ts] = ts_to_sum.get(ts, 0) + float(val)
                    except (TypeError, ValueError):
                        pass

    total_datapoints = [[v, t] for t, v in sorted(ts_to_sum.items())]

    total_count = sum(len(s.get("datapoints") or []) for s in series) + len(total_datapoints)
    reminder = "数据量过大，请缩小时间范围以减少数据量" if total_count > n else None

    out = []
    for s in series:
        datapoints = s.get("datapoints") or []
        stats = _extract_series_stats(datapoints)
        out.append({**s, **stats})

    # if len(series) > 1, add total series
    if len(series) > 1:
        total_series = {
            "dimensions": {"__aggregate__": "total"},
            "datapoints": total_datapoints,
            **_extract_series_stats(total_datapoints),
        }
        out.append(total_series)
        total_count += len(total_datapoints)

    if total_count > n:
        if start_time is not None and end_time is not None:
            reminder = (
                f"数据量过大({total_count} 条)，请缩小时间范围以减少数据量。"
                f" 查询时间范围：{timezone2timestamp(start_time)} 到 {timezone2timestamp(end_time)}"
            )
        else:
            reminder = f"数据量过大({total_count} 条)，请缩小时间范围以减少数据量"
        return out, reminder
    return out, None


# 毫秒时间戳下界
_MS_TS_THRESHOLD = 10**12


def _fmt_num(v: Any) -> str:
    """将数值格式化为紧凑字符串，整数不显示小数点。"""
    if v is None:
        return "-"
    try:
        f = float(v)
        if f == int(f) and abs(f) < 1e15:
            return str(int(f))
        return f"{f:.4g}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_ts(ts: Any) -> str:
    """将 Unix 时间戳（秒或毫秒）格式化为紧凑 UTC 字符串 MM-DD HH:MM。"""
    if ts is None:
        return "-"
    try:
        t = float(ts)
        if t >= _MS_TS_THRESHOLD:
            t /= 1000
        dt = datetime.datetime.utcfromtimestamp(t)
        return dt.strftime("%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return str(ts)


def _make_md_table(headers: List[str], rows: List[List[str]]) -> str:
    """将表头和行列表拼装为 Markdown 表格字符串。"""
    sep = "|" + "|".join("---" for _ in headers) + "|"
    lines = ["|" + "|".join(headers) + "|", sep]
    for row in rows:
        lines.append("|" + "|".join(str(c) for c in row) + "|")
    return "\n".join(lines)


def _series_to_markdown(series: List[Dict[str, Any]]) -> str:
    """将 series 列表转换为 Markdown 表格字符串，以减少 token 占用。

    输出逻辑：
    - 始终输出统计汇总表（维度列 + min/max/avg/max_time）。
    - 若总数据点 ≤ 120 且存在 datapoints，则在汇总表后追加每个 series 的详细数据点表。
    - instant 查询（每 series ≤1 个数据点）改为输出 value/time 表。
    """
    if not series:
        return "无数据"

    # 收集所有维度键（保序、去重）
    dim_keys: List[str] = []
    dim_keys_set: set = set()
    for s in series:
        for k in (s.get("dimensions") or {}).keys():
            if k not in dim_keys_set:
                dim_keys.append(k)
                dim_keys_set.add(k)

    has_datapoints = any(s.get("datapoints") for s in series)

    # instant 查询（每 series ≤1 个点）→ 简洁 value/time 表
    if has_datapoints and all(len(s.get("datapoints") or []) <= 1 for s in series):
        headers = dim_keys + ["value", "time"]
        rows = []
        for s in series:
            dims = s.get("dimensions") or {}
            row = [str(dims.get(k, "")) for k in dim_keys]
            dp = (s.get("datapoints") or [[None, None]])[0]
            val = dp[0] if dp else None
            ts = dp[1] if len(dp) > 1 else None
            row += [_fmt_num(val), _fmt_ts(ts)]
            rows.append(row)
        return _make_md_table(headers, rows)

    # 统计汇总表
    stat_headers = dim_keys + ["min", "max", "avg", "max_time"]
    stat_rows = []
    for s in series:
        dims = s.get("dimensions") or {}
        row = [str(dims.get(k, "")) for k in dim_keys]
        row += [
            _fmt_num(s.get("min")),
            _fmt_num(s.get("max")),
            _fmt_num(s.get("avg")),
            _fmt_ts(s.get("max_time")),
        ]
        stat_rows.append(row)
    stats_md = _make_md_table(stat_headers, stat_rows)

    if not has_datapoints:
        return stats_md

    # 数据点详情（仅在总点数 ≤ 120 时追加）
    total_dp = sum(len(s.get("datapoints") or []) for s in series)
    if total_dp > 120:
        return stats_md

    dp_parts = []
    for s in series:
        dims = s.get("dimensions") or {}
        dim_label = " ".join(f"{k}={v}" for k, v in dims.items() if v)
        datapoints = s.get("datapoints") or []
        dp_rows = [[_fmt_ts(pt[1]), _fmt_num(pt[0])] for pt in datapoints if len(pt) >= 2 and pt[0] is not None]
        if dp_rows:
            dp_parts.append(f"**{dim_label}**\n" + _make_md_table(["t", "v"], dp_rows))

    if dp_parts:
        return stats_md + "\n\n" + "\n\n".join(dp_parts)
    return stats_md


def _query_mongodb_metrics(
    cluster_domain: str,
    start_time: Any,
    end_time: Any,
    promql: str,
) -> Dict[str, Any]:
    """调用监控 unify_query 查询 MongoDB 指标，返回 series 或 error。"""
    end_ts = timezone2timestamp(end_time) if end_time else int(__import__("time").time())
    start_ts = timezone2timestamp(start_time) if start_time else end_ts - 2 * 60
    # if end_ts - start_ts > 30 * 60:
    #    return {"error": "Query time range too large. Limit 30 minutes."}
    # 如果时间范围小于 2 分钟，则使用 instant 类型，否则使用 range 类型
    is_instant = end_ts - start_ts <= 2 * 60
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = start_ts
    params["end_time"] = end_ts
    params["type"] = "instant" if is_instant else "range"
    params["step"] = "auto"
    params["query_configs"][0]["promql"] = promql

    try:
        resp = BKMonitorV3Api.unify_query(params)
        series = resp.get("series", [])
        series, reminder = _add_total_series_and_stats(series, start_time=start_time, end_time=end_time)
        result: Dict[str, Any] = {"series": series}
        if reminder:
            result["reminder"] = reminder
            # delete datapoints from series
            for s in series:
                s.pop("datapoints", None)
        # 若无数据且查询结束时间过早，提示可能因监控数据保留策略导致无数据
        if not series and (int(__import__("time").time()) - end_ts) > PAST_RANGE_HINT_DAYS * 86400:
            past_hint = f"查询时间范围结束于 {end_ts}，早于当前时间超过 {PAST_RANGE_HINT_DAYS} 天，" "可能因监控数据保留策略无数据，请尝试查询最近一段时间。"
            if result.get("reminder"):
                result["reminder"] = f"{result['reminder']}; {past_hint}"
            else:
                result["reminder"] = past_hint

        return result
    except Exception as e:
        logger.exception("mongodb metrics unify_query error: %s", e)
        return {"error": str(e)}


def get_mongodb_qps(
    cluster_domain: str,
    start_time: Any,
    end_time: Any,
    instance_host: Optional[str] = None,
    instance: Optional[str] = None,
) -> Dict[str, Any]:
    """查询 MongoDB QPS（op_counters 速率）。"""
    # mongos/proxy: mongodb_op_counters_total / mongodb_mongos_op_counters_total; shard: mongodb_mongod_op_counters_total
    inst = _instance_filter(instance_host)
    if instance:
        inst = f',instance="{instance}"'
    group_by_keys = ",".join(["type", "instance_role", "instance", "shard"])
    promql = (
        f"sum by ({group_by_keys}) (irate(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_op_counters_total"
        f'{{instance_role!="backup",cluster_domain="{cluster_domain}"{inst}}}[2m])) '
        f"or sum by ({group_by_keys}) (irate(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_op_counters_total"
        f'{{instance_role!="backup",cluster_domain="{cluster_domain}"{inst}}}[2m]))'
    )
    result = _query_mongodb_metrics(cluster_domain, start_time, end_time, promql)
    if "error" in result:
        return {"cluster_domain": cluster_domain, "metric_type": "qps", "table": "无数据", "error": result["error"]}
    out = {"cluster_domain": cluster_domain, "metric_type": "qps", "table": _series_to_markdown(result["series"])}
    if result.get("reminder"):
        out["reminder"] = result["reminder"]
    return out


def get_mongodb_connections(
    cluster_domain: str,
    start_time: Any,
    end_time: Any,
    instance_host: Optional[str] = None,
    instance: Optional[str] = None,
) -> Dict[str, Any]:
    """查询 MongoDB 连接数（current）。"""
    inst = _instance_filter(instance_host)
    if instance:
        inst = f',instance="{instance}"'
    # mongos/proxy: mongodb_connections; mongod: mongodb_mongod_connections（数据 1 分钟 1 条，用 max_over_time[5m] 取 5 个点最大）
    group_by_keys = ",".join(["instance", "instance_role", "shard", "state"])
    promql = (
        f"max by ({group_by_keys}) (max_over_time(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_connections"
        f'{{instance_role!="backup",cluster_domain="{cluster_domain}"{inst}}}[10m])) '
        f"or max by ({group_by_keys}) (max_over_time(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_connections"
        f'{{instance_role!="backup",cluster_domain="{cluster_domain}"{inst}}}[10m]))'
    )
    result = _query_mongodb_metrics(cluster_domain, start_time, end_time, promql)
    if "error" in result:
        return {
            "cluster_domain": cluster_domain,
            "metric_type": "connections",
            "table": "无数据",
            "error": result["error"],
        }
    out = {
        "cluster_domain": cluster_domain,
        "metric_type": "connections",
        "table": _series_to_markdown(result["series"]),
    }
    if result.get("reminder"):
        out["reminder"] = result["reminder"]
    return out


def get_mongodb_locks(
    cluster_domain: str,
    start_time: Any,
    end_time: Any,
    instance_host: Optional[str] = None,
    instance: Optional[str] = None,
) -> Dict[str, Any]:
    """查询 MongoDB 锁队列（global_lock current_queue）。数据 1 分钟 1 条，用 max_over_time[5m]。"""
    inst = _instance_filter(instance_host)
    if instance:
        inst = f',instance="{instance}"'
    group_by_keys = ",".join(["instance", "instance_role", "type", "shard"])
    metric = "bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_global_lock_current_queue"
    promql = (
        f"max by ({group_by_keys}) (max_over_time({metric}"
        f'{{instance_role!="backup",type!="total",cluster_domain="{cluster_domain}"{inst}}}[5m]))'
    )
    result = _query_mongodb_metrics(cluster_domain, start_time, end_time, promql)
    if "error" in result:
        return {"cluster_domain": cluster_domain, "metric_type": "locks", "table": "无数据", "error": result["error"]}
    out = {"cluster_domain": cluster_domain, "metric_type": "locks", "table": _series_to_markdown(result["series"])}
    if result.get("reminder"):
        out["reminder"] = result["reminder"]
    return out


def get_mongodb_cpu_usage(
    cluster_domain: str,
    start_time: Any,
    end_time: Any,
    instance_host: Optional[str] = None,
    instance: Optional[str] = None,
) -> Dict[str, Any]:
    """查询 MongoDB 主机 CPU 使用率。数据 1 分钟 1 条，用 max_over_time[5m]。"""
    inst = _instance_filter(instance_host)
    if instance:
        inst = f',instance="{instance}"'
    promql = (
        f"max by (cluster_domain, bk_target_ip, instance_role, shard) (max_over_time(bkmonitor:dbm_system:cpu_summary:usage"
        f'{{instance_role!="backup",cluster_domain="{cluster_domain}"{inst}}}[5m]))'
    )
    result = _query_mongodb_metrics(cluster_domain, start_time, end_time, promql)
    if "error" in result:
        return {
            "cluster_domain": cluster_domain,
            "metric_type": "cpu_usage",
            "table": "无数据",
            "error": result["error"],
        }
    out = {
        "cluster_domain": cluster_domain,
        "metric_type": "cpu_usage",
        "table": _series_to_markdown(result["series"]),
    }
    if result.get("reminder"):
        out["reminder"] = result["reminder"]
    return out
