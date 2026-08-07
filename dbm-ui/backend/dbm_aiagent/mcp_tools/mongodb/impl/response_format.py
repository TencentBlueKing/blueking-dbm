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
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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


# 慢日志 log.meta 精简字段：去掉与 instance 重复的 host/port，以及业务侧冗余标识
_SLOWLOG_META_KEEP = (
    "cluster_domain",
    "cluster_type",
    "instance_set_name",
    "instance",
    "instance_role",
)


def _maybe_parse_json(value: Any) -> Any:
    """字符串若为 JSON 则解析为对象/数组；失败或非字符串则原样返回。"""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value


def _slim_slowlog_meta(parsed: Any) -> Any:
    """解析成功的慢日志对象：只保留定位问题所需的 meta 字段。"""
    if not isinstance(parsed, dict):
        return parsed
    meta = parsed.get("meta")
    if not isinstance(meta, dict):
        return parsed
    slim = {k: meta[k] for k in _SLOWLOG_META_KEEP if k in meta and meta[k] not in (None, "")}
    out = dict(parsed)
    out["meta"] = slim
    return out


def _slowlog_list_item(doc: Any) -> Any:
    """优先取原始日志字段 log（尝试 JSON 解析并精简 meta）；没有再用整条文档。"""
    if isinstance(doc, dict):
        log = doc.get("log")
        if isinstance(log, str) and log:
            parsed = _maybe_parse_json(log)
            return _slim_slowlog_meta(parsed) if parsed is not log else log
    if isinstance(doc, str):
        parsed = _maybe_parse_json(doc)
        return _slim_slowlog_meta(parsed) if parsed is not doc else doc
    return doc


def format_slowlog_list(raw: Dict) -> Dict:
    """
    慢日志明细 → {"total", "items"}。
    有 log 字段时优先解析为 JSON（失败保留原字符串），并精简 meta；无 log 时退回整条文档。
    """
    entries = raw.get("slowlog_entries")
    items: List[Any] = []
    if isinstance(entries, list):
        items = [_slowlog_list_item(e) for e in entries]
    elif isinstance(entries, dict):
        hits = None
        hits_wrap = entries.get("hits")
        if isinstance(hits_wrap, dict):
            hits = hits_wrap.get("hits")
        if hits is None:
            hits = entries.get("list") or entries.get("docs")
        if isinstance(hits, list):
            for hit in hits:
                if isinstance(hit, dict) and isinstance(hit.get("_source"), dict):
                    items.append(_slowlog_list_item(hit["_source"]))
                else:
                    items.append(_slowlog_list_item(hit))
        else:
            items = [_slowlog_list_item(entries)]
    return {"total": len(items), "items": items}


def _es_aggs_root(resp: Any) -> Dict:
    if not isinstance(resp, dict):
        return {}
    aggs = resp.get("aggregations") or resp.get("aggs")
    return aggs if isinstance(aggs, dict) else {}


def _es_buckets(node: Any) -> List[Dict]:
    if not isinstance(node, dict):
        return []
    buckets = node.get("buckets") or []
    return [b for b in buckets if isinstance(b, dict)]


def _compact_ns_queryhash_aggs(resp: Any) -> List[Dict]:
    """ES by_ns → by_queryHash → [{ns, count, top_queryHash:[{queryHash,count}]}]"""
    by_ns = _es_aggs_root(resp).get("by_ns")
    out: List[Dict] = []
    for bucket in _es_buckets(by_ns):
        top_qh = [
            {"queryHash": qb.get("key", ""), "count": qb.get("doc_count", 0)}
            for qb in _es_buckets(bucket.get("by_queryHash"))
        ]
        out.append({"ns": bucket.get("key", ""), "count": bucket.get("doc_count", 0), "top_queryHash": top_qh})
    return out


def _compact_shard_instance_aggs(resp: Any) -> List[Dict]:
    """ES by_shard → by_instance → [{shard, count, instances:[{instance,count}]}]"""
    by_shard = _es_aggs_root(resp).get("by_shard")
    out: List[Dict] = []
    for bucket in _es_buckets(by_shard):
        instances = [
            {"instance": ib.get("key", ""), "count": ib.get("doc_count", 0)}
            for ib in _es_buckets(bucket.get("by_instance"))
        ]
        out.append({"shard": bucket.get("key", ""), "count": bucket.get("doc_count", 0), "instances": instances})
    return out


def format_slowlog_overview(raw: Dict) -> Dict:
    """慢日志聚合 → 精简桶 {by_ns, by_shard}，不透传原始 ES 包装。"""
    return {
        "by_ns": _compact_ns_queryhash_aggs(raw.get("aggr_by_ns_and_queryHash")),
        "by_shard": _compact_shard_instance_aggs(raw.get("aggr_by_shard_and_instance")),
    }
