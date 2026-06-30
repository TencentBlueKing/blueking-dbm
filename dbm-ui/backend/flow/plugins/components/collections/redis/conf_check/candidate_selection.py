# -*- coding: utf-8 -*-
"""
Candidate cluster selection for REDIS_CONF_CHECK periodic task.
Kept outside db_periodic_task.local_tasks so flow unit tests can import safely.
"""
from typing import Dict, List, Tuple

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster

from .registry import CHECKER_REGISTRY


def checker_query_filters(config, checker) -> Dict:
    """Merge global config with per-checker customized overrides for candidate selection."""
    overrides = (getattr(config, "customized", None) or {}).get(checker.name, {})
    cluster_types = overrides.get("cluster_types") or checker.cluster_types
    global_cluster_types = getattr(config, "cluster_types", None)
    if global_cluster_types:
        cluster_types = [ctype for ctype in cluster_types if ctype in global_cluster_types]
    return {
        "cluster_types": cluster_types,
        "bizs_ignored": overrides.get("bizs_ignored", getattr(config, "bizs_ignored", None)) or [],
        "clusters_ignored": overrides.get("clusters_ignored", getattr(config, "clusters_ignored", None)) or [],
        "bk_cloud_ids": overrides.get("bk_cloud_ids", getattr(config, "bk_cloud_ids", None)) or [],
    }


def get_candidate_cluster_tuples(config) -> List[Tuple[int, int]]:
    """Return deduplicated [(bk_cloud_id, cluster_id), ...] across all registered checkers."""
    seen = set()
    result: List[Tuple[int, int]] = []
    for checker in CHECKER_REGISTRY:
        filters = checker_query_filters(config, checker)
        if not filters["cluster_types"]:
            continue
        query = Cluster.objects.filter(
            cluster_type__in=filters["cluster_types"],
            phase=ClusterPhase.ONLINE,
        )
        if filters["bizs_ignored"]:
            query = query.exclude(bk_biz_id__in=filters["bizs_ignored"])
        if filters["clusters_ignored"]:
            query = query.exclude(id__in=filters["clusters_ignored"])
        if filters["bk_cloud_ids"]:
            query = query.filter(bk_cloud_id__in=filters["bk_cloud_ids"])
        for bk_cloud_id, cluster_id in query.values_list("bk_cloud_id", "id"):
            key = (bk_cloud_id, cluster_id)
            if key not in seen:
                seen.add(key)
                result.append(key)
    return result
