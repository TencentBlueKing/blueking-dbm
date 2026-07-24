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
from collections import defaultdict
from typing import Iterable, Optional

from django.utils import timezone

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import LevelName
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config import (
    SKIP_REPORT_MSG_PREFIX,
    ClusterCapacityGrowthCheckConfig,
)
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter import RedisAgentCheckTask
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.tasks.registry import ai_task
from backend.flow.consts import ConfigTypeEnum
from backend.flow.utils.redis.redis_report_utils import RedisReportWriter

logger = logging.getLogger("celery")

MAXMEMORY_POLICY_CONF_NAME = "maxmemory-policy"
MAXMEMORY_POLICY_NOEVICTION = "noeviction"
MAXMEMORY_POLICY_BATCH_SIZE = 20


def _normalize_policy(raw) -> str:
    return str(raw or "").strip().lower()


def _batch_query_maxmemory_policies(clusters: Iterable) -> dict[str, str]:
    """Batch-fetch cluster-level maxmemory-policy, grouped by type+version.

    Response shape (db-config ``BatchGetConfigItemResp``)::

        content: { <level_value>: { <conf_name>: <conf_value>, ... }, ... }

    For cluster-level queries, ``level_value`` is the immute domain. The API does
    not inherit upper levels; missing domains yield an empty policy. Each call is
    capped at ``MAXMEMORY_POLICY_BATCH_SIZE`` domains. Any batch API failure
    raises so the producer can abort.
    """
    clusters = [cluster for cluster in clusters if cluster is not None]
    if not clusters:
        return {}

    groups: dict[tuple[str, str], list] = defaultdict(list)
    for cluster in clusters:
        groups[(cluster.cluster_type, cluster.major_version)].append(cluster)

    policies: dict[str, str] = {}
    for (cluster_type, major_version), group in groups.items():
        for offset in range(0, len(group), MAXMEMORY_POLICY_BATCH_SIZE):
            chunk = group[offset : offset + MAXMEMORY_POLICY_BATCH_SIZE]
            domains = [cluster.immute_domain for cluster in chunk]
            data = DBConfigApi.batch_get_conf_item(
                params={
                    "conf_file": major_version,
                    "conf_name": MAXMEMORY_POLICY_CONF_NAME,
                    "conf_type": ConfigTypeEnum.DBConf,
                    "level_name": LevelName.CLUSTER,
                    "level_values": domains,
                    "namespace": cluster_type,
                }
            )
            content = (data or {}).get("content") or {}
            for cluster in chunk:
                domain = cluster.immute_domain
                row = content.get(domain) if isinstance(content, dict) else None
                if isinstance(row, dict):
                    policies[domain] = _normalize_policy(row.get(MAXMEMORY_POLICY_CONF_NAME))
                else:
                    policies[domain] = ""
    return policies


def _eviction_skip_reason(policy: str) -> str:
    """Return a skip reason when eviction is enabled; empty string means keep for produce."""
    if not policy or policy == MAXMEMORY_POLICY_NOEVICTION:
        return ""
    return f"maxmemory-policy={policy} enables eviction"


def _write_eviction_skip_report(cluster, subtype, reason: str) -> None:
    report_day = int(timezone.now().strftime("%Y%m%d"))
    RedisReportWriter().write_redis_report(
        cluster_id=cluster.id,
        subtype=subtype.value,
        cluster=cluster.immute_domain,
        cluster_type=cluster.cluster_type,
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=cluster.bk_cloud_id,
        report_day=report_day,
        creator="",
        state=ReportStateType.NORMAL.value,
        msg=f"{SKIP_REPORT_MSG_PREFIX} {reason}",
        shard="all",
        instance="all",
    )


def filter_produce_candidates(items: list[dict], subtype=RedisCheckSubType.ClusterCapacityGrowthRisk) -> list[dict]:
    """Producer-side prune: drop eviction-enabled clusters and write NORMAL skip reports.

    Call this before ``task.submit(items)``. Dispatch itself does not select items.
    A batch dbconfig query failure raises: the producer must hold its cursor /
    priority pass and retry next beat rather than mistake a transient API blip
    for "nothing to produce" and skip a full rotation (or a day of alarm checks).
    """
    if not items:
        return []

    cluster_ids = [item.get("cluster_id") for item in items if item.get("cluster_id") is not None]
    clusters_by_id = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}

    resolved: list[tuple[dict, Optional[object]]] = []
    for item in items:
        cluster = item.get("cluster") or clusters_by_id.get(item.get("cluster_id"))
        resolved.append((item, cluster))

    policies = _batch_query_maxmemory_policies(cluster for _, cluster in resolved if cluster is not None)

    kept: list[dict] = []
    for item, cluster in resolved:
        if cluster is None:
            kept.append(item)
            continue
        policy = policies.get(cluster.immute_domain, "")
        reason = _eviction_skip_reason(policy)
        if not reason:
            kept.append(item)
            continue
        try:
            _write_eviction_skip_report(cluster, subtype, reason)
        except Exception as exc:
            logger.warning(
                "redis.cluster_capacity_growth: skip report failed cluster_id=%s: %s",
                cluster.id,
                exc,
            )
        logger.info(
            "redis.cluster_capacity_growth: produce skip cluster_id=%s reason=%s",
            cluster.id,
            reason,
        )
    return kept


@ai_task(
    agent_code=DBMAgentCode.REDIS_CLUSTER_CAPACITY_GROWTH_CHECK,
    config_cls=ClusterCapacityGrowthCheckConfig,
    db_type="redis",
)
class CheckClusterCapacityGrowthTask(RedisAgentCheckTask):
    """Dispatcher for the Redis cluster capacity growth LLM check."""

    subtype = RedisCheckSubType.ClusterCapacityGrowthRisk
    prompt_template = "cluster_domains: [{cluster_domain}]"
