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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def format_current_time(timestamps: Optional[List[int]] = None, time_strs: Optional[List[str]] = None) -> Dict:
    """对齐 redis_dashboard get_current_time：返回 utc / cst。"""
    utc_now = datetime.now(timezone.utc)
    cst_now = utc_now.astimezone(timezone(timedelta(hours=8)))
    out = {
        "utc": utc_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cst": cst_now.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }
    if time_strs is not None:
        out["time_strs"] = time_strs
    return out


def format_results(data: Any) -> Dict:
    """
    列表类元数据 → {"results": [...], "count": N}
    get_meta_info / 带 error 的 dict → {"error": "..."}
    单对象 → {"result": {...}}
    """
    if isinstance(data, list):
        return {"results": data, "count": len(data)}

    if not isinstance(data, dict):
        return {"result": data}

    err = data.get("error")
    if err:
        return {"error": err}

    if "meta_list" in data:
        results = data.get("meta_list") or []
        return {"results": results, "count": len(results)}

    for key in ("mongos", "shards"):
        if key in data and isinstance(data[key], list):
            return {"results": data[key], "count": len(data[key])}

    return {"result": data}


def _iso_from_unix(ts: Any) -> Optional[str]:
    if ts is None:
        return None
    try:
        ts_f = float(ts)
        if ts_f > 1e12:  # ms
            ts_f = ts_f / 1000.0
        return datetime.fromtimestamp(ts_f, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OSError):
        return None


def format_cluster_alarms(raw: Dict) -> Dict:
    """集群告警 → {"total", "items"}，item 字段对齐 redis get_active_alarms 风格。"""
    items: List[Dict] = []
    for group in raw.get("alarm_detail") or []:
        name = group.get("alert_name", "")
        for a in group.get("alert_detail") or []:
            items.append(
                {
                    "strategy_name": name,
                    "description": a.get("description", ""),
                    "level": a.get("severity") or a.get("level"),
                    "fired_at": _iso_from_unix(a.get("begin_time")),
                    "target_key": a.get("target_key", ""),
                    "instance_role": a.get("instance_role", ""),
                    "app": a.get("app", ""),
                }
            )
    return {"total": len(items), "items": items}


def format_biz_alarms(raw_flat: Dict) -> Dict:
    """业务告警扁平结构 → {"total", "items"}，带 cluster_domain。"""
    items: List[Dict] = []
    for domain, by_name in (raw_flat or {}).items():
        if not isinstance(by_name, dict):
            continue
        for name, alarms in by_name.items():
            for a in alarms or []:
                items.append(
                    {
                        "cluster_domain": domain,
                        "strategy_name": name,
                        "description": a.get("description", ""),
                        "level": a.get("severity") or a.get("level"),
                        "fired_at": _iso_from_unix(a.get("begin_time")),
                        "target_key": a.get("target_key", ""),
                        "instance_role": a.get("instance_role", ""),
                        "app": a.get("app", ""),
                    }
                )
    return {"total": len(items), "items": items}


def _normalize_slowlog_item(entry: Any) -> Dict:
    if not isinstance(entry, dict):
        return {"raw": entry}
    # BKLog hit 可能包在 _source
    src = entry.get("_source") if "_source" in entry else entry
    meta = src.get("meta") or {}
    attr = src.get("attr") or {}
    duration = src.get("durationMillis")
    if duration is None:
        duration = attr.get("durationMillis") or src.get("duration_ms")
    create_time = src.get("create_time") or src.get("dtEventTimeStamp") or src.get("timestamp")
    return {
        "timestamp": create_time if isinstance(create_time, str) else _iso_from_unix(create_time),
        "duration_ms": duration,
        "op": attr.get("op") or src.get("op", ""),
        "ns": attr.get("ns") or src.get("ns", ""),
        "queryHash": attr.get("queryHash") or src.get("queryHash", ""),
        "instance_host": meta.get("instance_host") or src.get("instance_host", ""),
        "instance": meta.get("instance") or src.get("instance_addr") or src.get("instance", ""),
        "instance_role": meta.get("instance_role") or src.get("instance_role", ""),
    }


def format_slowlog_list(raw: Dict) -> Dict:
    """慢日志明细 → {"total", "items"}。"""
    entries = raw.get("slowlog_entries")
    items: List[Dict] = []
    if isinstance(entries, list):
        items = [_normalize_slowlog_item(e) for e in entries]
    elif isinstance(entries, dict):
        hits = entries.get("hits", {}).get("hits") if isinstance(entries.get("hits"), dict) else None
        if hits is None:
            hits = entries.get("list") or entries.get("docs") or []
        if isinstance(hits, list):
            items = [_normalize_slowlog_item(e) for e in hits]
    return {"total": len(items), "items": items}


def format_slowlog_overview(raw: Dict) -> Dict:
    """慢日志聚合 → {"summary": {...}}。"""
    return {
        "summary": {
            "by_ns_and_queryHash": raw.get("aggr_by_ns_and_queryHash"),
            "by_shard_and_instance": raw.get("aggr_by_shard_and_instance"),
        }
    }
