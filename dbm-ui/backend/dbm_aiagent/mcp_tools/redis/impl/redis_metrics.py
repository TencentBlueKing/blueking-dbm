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
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, MetricsInstanceRole, MetricType
from backend.dbm_aiagent.mcp_tools.redis.models import InstanceFilter, MetricsQueryBatch
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_metrics_svc import RedisMetricsQueryService
from backend.dbm_aiagent.mcp_tools.redis.utils import calculate_time_range_window

_PROXY_ONLY_METRICS = {MetricType.LATENCY_DISTRIBUTION}
# CAPACITY is backend-only. instance_cpu_usage works for Redis backend and Twemproxy proxy;
# Predixy proxy has no process CPU metric and is rejected at metric-key resolve time.
_BACKEND_ONLY_METRICS = {MetricType.CAPACITY}


@dataclass
class ResolutionResult:
    batches: Optional[List[MetricsQueryBatch]] = None
    time_range: Optional[tuple] = None
    # unify_query step/interval seconds (datapoint spacing); PromQL lookback is fixed separately
    time_window: Optional[int] = None
    error: Optional[dict] = None
    partial_errors: Optional[List[dict]] = None


def _validate_metric_role(
    metric_type: MetricType,
    instance_role: MetricsInstanceRole,
    ip: Optional[str] = None,
) -> Optional[dict]:
    """Return an error dict if metric_type is incompatible with instance_role, else None.

    Cluster proxy/backend metric sets are enforced in MCP serializers; this remains for
    machine/instance APIs where role is resolved at runtime (proxy vs backend).
    """
    role_context = f" (auto-resolved role for IP {ip}: {instance_role.value})" if ip else ""
    if metric_type in _PROXY_ONLY_METRICS and instance_role != MetricsInstanceRole.PROXY:
        return {"error": f"metric_type '{metric_type.value}' is only available for proxy nodes{role_context}"}
    if metric_type in _BACKEND_ONLY_METRICS and instance_role == MetricsInstanceRole.PROXY:
        return {"error": f"metric_type '{metric_type.value}' is not available for proxy nodes{role_context}"}
    return None


def _detect_storage_role(instance_role: str) -> MetricsInstanceRole:
    """Map a StorageInstance's instance_role to the corresponding MetricsInstanceRole."""
    if instance_role == InstanceRole.REDIS_SLAVE:
        return MetricsInstanceRole.SLAVE
    if instance_role == InstanceRole.REDIS_MASTER:
        return MetricsInstanceRole.MASTER
    raise ValueError(f"Unsupported storage instance role for metrics query: {instance_role}")


def _resolve_err(message: str):
    return ResolutionResult(error={"error": message})


class _Resolved(NamedTuple):
    cluster: Optional[Cluster]
    role: Optional[MetricsInstanceRole]
    error: Optional[str]


_err = lambda msg: _Resolved(None, None, msg)  # noqa: E731


def _fetch_clusters(domains: Iterable[str]) -> Dict[str, Cluster]:
    """Fetch Cluster objects for the given immute_domain values, keyed by domain."""
    return {c.immute_domain: c for c in Cluster.objects.filter(immute_domain__in=list(set(domains)))}


def _determine_role(cluster: Cluster, is_proxy: bool, storage_role_str: Optional[str], label: str) -> _Resolved:
    """Given proxy/storage lookup results, return the resolved instance."""
    if is_proxy:
        return _Resolved(cluster, MetricsInstanceRole.PROXY, None)
    if storage_role_str is not None:
        try:
            return _Resolved(cluster, _detect_storage_role(storage_role_str), None)
        except ValueError as e:
            return _err(str(e))
    return _err(f"No proxy or storage instance found for {label} in cluster {cluster.immute_domain}")


def _classify_ip_domains(
    ip_to_domains: Dict[str, Set[str]],
    ips: List[str],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """IPs with exactly one cluster domain vs IPs with an error message."""
    ok: Dict[str, str] = {}
    err: Dict[str, str] = {}
    for ip in ips:
        doms = ip_to_domains.get(ip) or set()
        if not doms:
            err[ip] = f"No cluster found for IP: {ip}"
        elif len(doms) > 1:
            err[ip] = f"Abnormal: IP {ip} belongs to multiple clusters: {sorted(doms)}."
        else:
            ok[ip] = next(iter(doms))
    return ok, err


def _batch_resolve(
    ips: Optional[List[str]] = None,
    pairs: Optional[List[Tuple[str, int]]] = None,
) -> dict:
    """Resolve IPs or ip:port pairs to (cluster, role) in batched DB queries.

    Pass *either* ips (machine-level) or pairs (instance-level), not both.
    Returns Dict[key, _Resolved] where key is str (IP) or Tuple[str, int] (pair).
    """
    by_pair = pairs is not None
    if by_pair:
        unique_keys = list(dict.fromkeys(pairs))
        unique_ips = list(dict.fromkeys(ip for ip, _ in unique_keys))
    else:
        unique_keys = list(dict.fromkeys(ips or []))
        unique_ips = unique_keys

    if not unique_keys:
        return {}

    ip_to_domains: Dict[str, Set[str]] = defaultdict(set)
    ip_has_proxy: Set[str] = set()
    proxy_pairs: Set[Tuple[str, int]] = set()
    ip_storage_role: Dict[str, str] = {}
    storage_role_by_pair: Dict[Tuple[str, int], str] = {}

    for ip, port, dom in (
        ProxyInstance.objects.filter(machine__ip__in=unique_ips)
        .exclude(cluster__immute_domain="")
        .values_list("machine__ip", "port", "cluster__immute_domain")
    ):
        if dom:
            ip_to_domains[ip].add(dom)
            ip_has_proxy.add(ip)
            proxy_pairs.add((ip, port))

    for row in (
        StorageInstance.objects.filter(machine__ip__in=unique_ips)
        .exclude(cluster__immute_domain="")
        .order_by("id")
        .values("machine__ip", "port", "cluster__immute_domain", "instance_role")
    ):
        dom = row["cluster__immute_domain"]
        if not dom:
            continue
        ip = row["machine__ip"]
        ip_to_domains[ip].add(dom)
        ip_storage_role.setdefault(ip, row["instance_role"])
        storage_role_by_pair.setdefault((ip, row["port"]), row["instance_role"])

    ip_to_domain, ip_err = _classify_ip_domains(dict(ip_to_domains), unique_ips)

    result: dict = {}
    if not ip_to_domain:
        for key in unique_keys:
            if by_pair:
                label = f"{key[0]}:{key[1]}"
                k_ip = key[0]
            else:
                label = f"IP {key}"
                k_ip = key
            result[key] = _err(ip_err.get(k_ip, f"No cluster found for {label}"))
        return result

    clusters = _fetch_clusters(ip_to_domain.values())

    for key in unique_keys:
        if by_pair:
            ip, port = key
            label = f"{ip}:{port}"
        else:
            ip = key
            label = f"IP {ip}"

        if ip in ip_err:
            result[key] = _err(ip_err[ip])
            continue

        cluster = clusters.get(ip_to_domain[ip])
        if not cluster:
            result[key] = _err(f"No cluster found for {label}")
            continue

        if by_pair:
            is_proxy = key in proxy_pairs
            storage_role = storage_role_by_pair.get(key)
        else:
            is_proxy = ip in ip_has_proxy
            storage_role = ip_storage_role.get(ip)

        result[key] = _determine_role(cluster, is_proxy, storage_role, label)

    return result


def _build_node_batches(
    resolved_items: List[Tuple[str, Cluster, MetricsInstanceRole, Optional[str], Optional[InstanceFilter]]],
) -> List[MetricsQueryBatch]:
    """Group resolved entries by role and build one MetricsQueryBatch per group.

    Each item is (meta_key, cluster, role, ip_filter_or_none, instance_filter_or_none).
    Cluster objects are carried forward directly -- no re-fetch needed.
    """
    role_groups: Dict[MetricsInstanceRole, Dict] = defaultdict(
        lambda: {"clusters": {}, "ip_filters": [], "instance_filters": [], "entity_meta": {}}
    )

    for meta_key, cluster, role, ip_filter, instance_filter in resolved_items:
        group = role_groups[role]
        group["clusters"][cluster.id] = cluster
        if ip_filter is not None:
            group["ip_filters"].append(ip_filter)
        if instance_filter is not None:
            group["instance_filters"].append(instance_filter)
        group["entity_meta"][meta_key] = {
            "cluster_domain": cluster.immute_domain,
            "cluster_type": str(cluster.cluster_type),
        }

    return [
        MetricsQueryBatch(
            clusters=list(group["clusters"].values()),
            instance_role=role,
            ip_filters=group["ip_filters"] or None,
            instance_filters=group["instance_filters"] or None,
            entity_meta=group["entity_meta"],
        )
        for role, group in role_groups.items()
    ]


def resolve_cluster_from_domain(
    cluster_domains: List[str],
    instance_role: MetricsInstanceRole,
    max_len_datapoints: int,
    start_time,
    end_time,
    enforce_max_datapoints_limit: bool = True,
) -> ResolutionResult:
    """Resolve clusters by domain, build a single batch with the given role."""
    clusters = list(Cluster.objects.filter(immute_domain__in=cluster_domains))
    found_domains = {cluster.immute_domain for cluster in clusters}
    missing_domains = sorted(set(cluster_domains) - found_domains)
    if missing_domains:
        return _resolve_err(f"Cluster not found: {missing_domains}. Verify domains exist in db_meta and spelling.")

    time_range, time_window = calculate_time_range_window(
        max_len_datapoints, start_time, end_time, enforce_max_datapoints_limit=enforce_max_datapoints_limit
    )
    entity_meta = {
        c.immute_domain: {"cluster_domain": c.immute_domain, "cluster_type": str(c.cluster_type)} for c in clusters
    }
    batches = [MetricsQueryBatch(clusters=clusters, instance_role=instance_role, entity_meta=entity_meta)]
    return ResolutionResult(batches=batches, time_range=time_range, time_window=time_window)


def resolve_cluster_from_ip(
    ips: List[str],
    max_len_datapoints: int,
    start_time,
    end_time,
    enforce_max_datapoints_limit: bool = True,
) -> ResolutionResult:
    """Resolve clusters and instance_role from IPs, auto-grouping by role."""
    resolved_by_ip = _batch_resolve(ips=ips)
    items = []
    partial_errors: List[dict] = []
    for ip in ips:
        cluster, role, err = resolved_by_ip[ip]
        if err:
            partial_errors.append({"error": err, "ip": ip})
            continue
        items.append((ip, cluster, role, ip, None))

    if not items:
        return _resolve_err(f"All IPs failed resolution: {[e['error'] for e in partial_errors]}")

    time_range, time_window = calculate_time_range_window(
        max_len_datapoints, start_time, end_time, enforce_max_datapoints_limit=enforce_max_datapoints_limit
    )
    return ResolutionResult(
        batches=_build_node_batches(items),
        time_range=time_range,
        time_window=time_window,
        partial_errors=partial_errors or None,
    )


def resolve_cluster_from_instances(
    instances: List[dict],
    max_len_datapoints: int,
    start_time,
    end_time,
    enforce_max_datapoints_limit: bool = True,
) -> ResolutionResult:
    """Resolve clusters and instance_role from explicit ip:port pairs, auto-grouping by role."""
    seen = set()
    ordered_pairs: List[Tuple[str, int]] = []
    for instance in instances:
        pair = (instance["ip"], int(instance["port"]))
        if pair in seen:
            continue
        seen.add(pair)
        ordered_pairs.append(pair)

    pair_results = _batch_resolve(pairs=ordered_pairs)
    items = []
    partial_errors: List[dict] = []
    for ip, port in ordered_pairs:
        cluster, role, err = pair_results[(ip, port)]
        if err:
            partial_errors.append({"error": err, "instance": f"{ip}:{port}"})
            continue
        items.append((f"{ip}:{port}", cluster, role, None, InstanceFilter(ip=ip, port=port)))

    if not items:
        return _resolve_err(f"All instances failed resolution: {[e['error'] for e in partial_errors]}")

    time_range, time_window = calculate_time_range_window(
        max_len_datapoints, start_time, end_time, enforce_max_datapoints_limit=enforce_max_datapoints_limit
    )
    return ResolutionResult(
        batches=_build_node_batches(items),
        time_range=time_range,
        time_window=time_window,
        partial_errors=partial_errors or None,
    )


def _merge_entity_meta(batches: List[MetricsQueryBatch]) -> Dict[str, dict]:
    """Merge entity_meta from all batches, grouped by cluster_domain."""
    clusters: Dict[str, dict] = {}
    for batch in batches:
        if batch.entity_meta:
            for key, meta_val in batch.entity_meta.items():
                domain = meta_val["cluster_domain"]
                if domain not in clusters:
                    clusters[domain] = {"cluster_type": meta_val["cluster_type"], "entities": []}
                clusters[domain]["entities"].append({"key": key, "instance_role": batch.instance_role.value})
    return clusters


def query_redis_metrics_series(
    batches: List[MetricsQueryBatch],
    metric_type: MetricType,
    time_range: tuple,
    time_window: int,
    group_by: Optional[List[MetricsGroupBy]] = None,
    include_meta: bool = False,
) -> dict:
    """
    Query Redis cluster time-series metrics.

    Iterates over batches (each with a single instance_role), queries per batch,
    and merges results. Returns aggregated time series data.
    """
    metrics_svc = RedisMetricsQueryService()
    merged_series_by_scope: Dict[str, object] = {}
    all_partial_errors: List[dict] = []

    for batch in batches:
        ref_ip = (
            batch.ip_filters[0]
            if batch.ip_filters
            else (batch.instance_filters[0].ip if batch.instance_filters else None)
        )
        err = _validate_metric_role(metric_type, batch.instance_role, ref_ip)
        if err:
            all_partial_errors.append(err)
            continue

        series_by_scope, partial_errors = metrics_svc.query_metrics(
            clusters=batch.clusters,
            metric_type=metric_type,
            time_range=time_range,
            time_window=time_window,
            instance_role=batch.instance_role,
            ip_filters=batch.ip_filters,
            instance_filters=batch.instance_filters,
            group_by=group_by,
        )

        merged_series_by_scope.update(series_by_scope)
        all_partial_errors.extend(partial_errors)

    result_series = {}
    for entity_key, metric_series in merged_series_by_scope.items():
        for series_key, datapoints in (metric_series.raw_series or {}).items():
            if len(merged_series_by_scope) == 1 or entity_key == series_key:
                result_series[series_key] = datapoints
            else:
                result_series[f"{entity_key}@{series_key}"] = datapoints
    if not result_series and all_partial_errors:
        return {"error": "No metric series returned", "partial_errors": all_partial_errors}

    result = {"series": result_series}

    if include_meta:
        entity_meta = _merge_entity_meta(batches)
        if entity_meta:
            result["meta"] = entity_meta

    if all_partial_errors:
        result["partial_errors"] = all_partial_errors

    return result


def query_redis_metrics_stats(
    batches: List[MetricsQueryBatch],
    metric_type: MetricType,
    time_range: tuple,
    time_window: int,
    group_by: Optional[List[MetricsGroupBy]] = None,
    include_meta: bool = False,
) -> dict:
    """
    Query Redis cluster scalar statistics over the timeline.

    Iterates over batches (each with a single instance_role), queries per batch, and merges
    results. Each series is reduced to timeline statistics (min, max, avg, median, p95, cv,
    trend, latest) computed over the query window.
    """
    metrics_svc = RedisMetricsQueryService()
    merged_series_by_scope: Dict[str, object] = {}
    all_partial_errors: List[dict] = []

    for batch in batches:
        ref_ip = (
            batch.ip_filters[0]
            if batch.ip_filters
            else (batch.instance_filters[0].ip if batch.instance_filters else None)
        )
        err = _validate_metric_role(metric_type, batch.instance_role, ref_ip)
        if err:
            all_partial_errors.append(err)
            continue

        series_by_scope, partial_errors = metrics_svc.query_metrics(
            clusters=batch.clusters,
            metric_type=metric_type,
            time_range=time_range,
            time_window=time_window,
            instance_role=batch.instance_role,
            ip_filters=batch.ip_filters,
            instance_filters=batch.instance_filters,
            group_by=group_by,
        )

        merged_series_by_scope.update(series_by_scope)
        all_partial_errors.extend(partial_errors)

    result_statistics = {}
    for entity_key, metric_series in merged_series_by_scope.items():
        for stats_key, stats_value in (metric_series.statistics or {}).items():
            if len(merged_series_by_scope) == 1 or entity_key == stats_key:
                result_statistics[stats_key] = stats_value
            else:
                result_statistics[f"{entity_key}@{stats_key}"] = stats_value
    if not result_statistics and all_partial_errors:
        return {"error": "No metric statistics returned", "partial_errors": all_partial_errors}

    result = {"statistics": result_statistics}

    if include_meta:
        entity_meta = _merge_entity_meta(batches)
        if entity_meta:
            result["meta"] = entity_meta

    if all_partial_errors:
        result["partial_errors"] = all_partial_errors
    return result
