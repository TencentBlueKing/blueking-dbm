# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations of the License.
"""
from datetime import datetime
from typing import Dict, List, Optional

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.models import MetaCheckReport, RedisCheckReport
from backend.dbm_aiagent.mcp_tools.common.impl.biz_helpers import get_biz_by_abbr
from backend.dbm_aiagent.mcp_tools.redis.constants import (
    CREATABLE_REPORT_SUBTYPES,
    REPORT_MODEL_MAP,
    REPORT_SUBTYPE_MAP,
)
from backend.dbm_aiagent.mcp_tools.redis.enums import RedisReportSubtype

REDIS_CLUSTER_TYPE_VALUES = [ct.value for ct in ClusterType.redis_cluster_types()]

COMMON_OUTPUT_FIELDS = (
    "bk_biz_id",
    "cluster",
    "cluster_type",
    "shard",
    "instance",
    "subtype",
    "msg",
    "create_at",
    "failed_days",
    "state",
)


def resolve_biz_ids_for_query(bk_biz_id: Optional[int] = None, app_abbr: Optional[str] = None) -> List[int]:
    """Resolve bk_biz_id or bk_biz_abbr to a biz ID list."""
    if bk_biz_id is not None:
        return [bk_biz_id]
    if app_abbr:
        return get_biz_by_abbr(app_abbr)
    return []


def _resolve_models_and_subtype_values(
    subtypes: Optional[List[str]],
):
    """
    Resolve which models to query and subtype values per model.
    Returns: [(model, subtype_values), ...]
    """
    if subtypes:
        selected = [RedisReportSubtype(s) for s in subtypes]
    else:
        selected = list(RedisReportSubtype)
    model_subtype_values = {}
    for st in selected:
        model = REPORT_MODEL_MAP[st]
        db_value = REPORT_SUBTYPE_MAP[st].value
        model_subtype_values.setdefault(model, []).append(db_value)
    return list(model_subtype_values.items())


def _resolve_cluster_info(cluster_id: Optional[int] = None, cluster_domain: Optional[str] = None) -> dict:
    """Resolve cluster info by id or domain. Returns dict with cluster_domain, id, cluster_type."""
    fields = ("immute_domain", "id", "cluster_type", "bk_cloud_id", "bk_biz_id")
    if cluster_id:
        row = Cluster.objects.filter(id=cluster_id).values(*fields).get()
    elif cluster_domain:
        row = Cluster.objects.filter(immute_domain=cluster_domain).values(*fields).get()
    else:
        raise ValueError("cluster_id or cluster_domain is required")
    if not row:
        lookup = f"id={cluster_id}" if cluster_id else f"domain={cluster_domain!r}"
        raise ValueError(f"Cluster not found: {lookup}")
    return row


def _normalize_meta_check_row(row: dict) -> dict:
    """Map MetaCheckReport row (ip, port) to common schema (instance, shard)."""
    ip = row.get("ip")
    port = row.get("port")
    instance = f"{ip}:{port}" if ip is not None and port is not None else ""
    out = dict(row)
    out["instance"] = instance
    out["shard"] = ""
    out.pop("ip", None)
    out.pop("port", None)
    return out


def _deduplicate_latest_per_group(rows: List[dict]) -> List[dict]:
    """Keep only the latest record for each (subtype, cluster) pair.

    Assumes rows are already sorted by create_at descending so the first
    occurrence of each key is guaranteed to be the most recent one.
    """
    seen: set = set()
    result = []
    for row in rows:
        key = (row["subtype"], row["cluster"])
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _query_single_model(
    model,
    subtype_values: List[str],
    bk_biz_ids: Optional[List[int]] = None,
    cluster_domain: Optional[str] = None,
    states: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
) -> List[dict]:
    """Query one report model and return normalized rows.

    Returns at most one record per (subtype, cluster) pair — the latest one.
    The caller's *limit* is enforced after deduplication by _merge_and_limit.
    """
    queryset = model.objects.all()
    if bk_biz_ids:
        queryset = queryset.filter(bk_biz_id__in=bk_biz_ids)
    if cluster_domain:
        queryset = queryset.filter(cluster=cluster_domain)
    queryset = queryset.filter(subtype__in=subtype_values)
    queryset = queryset.filter(cluster_type__in=REDIS_CLUSTER_TYPE_VALUES)
    if states:
        queryset = queryset.filter(state__in=states)
    if start_time:
        queryset = queryset.filter(create_at__gte=start_time)
    if end_time:
        queryset = queryset.filter(create_at__lte=end_time)
    queryset = queryset.order_by("-create_at")

    if model is RedisCheckReport:
        rows = list(queryset.values(*COMMON_OUTPUT_FIELDS))
    elif model is MetaCheckReport:
        raw_rows = list(
            queryset.values(
                "bk_biz_id",
                "cluster",
                "cluster_type",
                "ip",
                "port",
                "subtype",
                "msg",
                "create_at",
                "failed_days",
                "state",
            )
        )
        rows = [_normalize_meta_check_row(r) for r in raw_rows]
    else:
        rows = list(queryset.values(*COMMON_OUTPUT_FIELDS))

    return _deduplicate_latest_per_group(rows)


def _merge_and_limit(
    all_items: List[dict],
    limit: int,
) -> dict:
    """Merge rows from multiple models, sort by create_at desc, slice to limit."""
    sorted_items = sorted(all_items, key=lambda x: x["create_at"], reverse=True)
    items = sorted_items[:limit]
    return {"total": len(items), "items": items}


def query_redis_reports_by_biz(
    bk_biz_ids: List[int],
    cluster_domain: Optional[str] = None,
    subtypes: Optional[List[str]] = None,
    states: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
):
    """Query Redis check reports by business ID(s)."""
    model_subtype_pairs = _resolve_models_and_subtype_values(subtypes)
    all_items = []
    for model, subtype_values in model_subtype_pairs:
        rows = _query_single_model(
            model,
            subtype_values,
            bk_biz_ids=bk_biz_ids,
            cluster_domain=cluster_domain,
            states=states,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        all_items.extend(rows)
    return _merge_and_limit(all_items, limit)


def query_redis_reports_by_cluster(
    cluster_domain: str,
    subtypes: Optional[List[str]] = None,
    states: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
):
    """Query Redis check reports by cluster domain."""
    model_subtype_pairs = _resolve_models_and_subtype_values(subtypes)
    all_items = []
    for model, subtype_values in model_subtype_pairs:
        rows = _query_single_model(
            model,
            subtype_values,
            cluster_domain=cluster_domain,
            states=states,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        all_items.extend(rows)
    return _merge_and_limit(all_items, limit)


def create_report_record(
    *,
    subtype: str,
    cluster_domain: Optional[str] = None,
    cluster_id: Optional[int] = None,
    msg: str,
    creator: str,
    state: str = "normal",
    shard: Optional[str] = None,
    instance: Optional[str] = None,
) -> Dict:
    """Create a Redis check report record. Subtype must be in CREATABLE_REPORT_SUBTYPES."""
    cluster_info = _resolve_cluster_info(cluster_id=cluster_id, cluster_domain=cluster_domain)
    st = RedisReportSubtype(subtype)
    if st not in CREATABLE_REPORT_SUBTYPES:
        raise ValueError(f"subtype {subtype!r} is not in CREATABLE_REPORT_SUBTYPES")
    db_subtype_value = REPORT_SUBTYPE_MAP[st].value
    model = REPORT_MODEL_MAP[st]
    if model is not RedisCheckReport:
        raise ValueError(f"subtype {subtype!r} maps to {model.__name__}, only RedisCheckReport is supported")
    record = RedisCheckReport.upsert_by_cluster_subtype(
        cluster_id=cluster_info["id"],
        subtype=db_subtype_value,
        cluster=cluster_info["immute_domain"],
        cluster_type=cluster_info["cluster_type"],
        bk_biz_id=cluster_info["bk_biz_id"],
        bk_cloud_id=cluster_info["bk_cloud_id"],
        report_day=int(datetime.now().strftime("%Y%m%d")),
        creator=creator,
        state=state,
        msg=msg,
        shard=shard or "",
        instance=instance or "",
    )
    return {"id": record.pk}
