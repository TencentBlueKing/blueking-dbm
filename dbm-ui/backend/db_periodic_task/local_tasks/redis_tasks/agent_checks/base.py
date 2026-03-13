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
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from datetime import timedelta
from typing import Callable

from django.db.models import Q
from django.utils import timezone

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.models import RedisCheckReport
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models import ClusterOperateRecord

logger = logging.getLogger("root")

# Redis ticket types that affect cluster stability (capacity/autofix/migrate)
REDIS_EXCLUSIVE_TICKET_TYPES = [
    TicketType.REDIS_SCALE_UPDOWN.value,
    TicketType.REDIS_CLUSTER_AUTOFIX.value,
    TicketType.REDIS_CLUSTER_INS_MIGRATE.value,
    TicketType.REDIS_SINGLE_INS_MIGRATE.value,
    TicketType.REDIS_DTS_ONLINE_SWITCH.value,
    TicketType.REDIS_MASTER_SLAVE_SWITCH.value,
    TicketType.REDIS_CLUSTER_CUTOFF.value,
    TicketType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
    TicketType.REDIS_CLUSTER_TYPE_UPDATE.value,
    TicketType.REDIS_CLUSTER_REINSTALL_DBMON.value,
]

TICKET_RUNNING_STATUS_VALUES = [s.value for s in TICKET_RUNNING_STATUS_SET]

DEFAULT_LOOKBACK_DAYS = 7


@dataclass
class BaseCheckConfig:
    enabled: bool = False
    batch_size: int = 40
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ignore_cluster_domains: list = field(default_factory=list)
    cluster_types: list = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict):
        valid_keys = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in valid_keys})


class BaseRedisAgentCheckTask(ABC):
    """Base class for Redis periodic LLM agent check tasks.

    Subclasses declare which report subtype they own, which agent to invoke,
    and provide a config. The shared dispatcher, dedup, and skip logic live here.

    To add a new check type:
      1. Create a thin subclass declaring `subtype`, `agent_code`, `prompt_template`, and `load_config()`.
      2. Define a Celery task function that calls `should_skip()` + `AgentHandler.ask_agent_with_content`.
      3. Register a periodic task in task.py.
    """

    # Subclasses must declare these:
    subtype: RedisCheckSubType
    agent_code: DBMAgentCode
    prompt_template: str  # plain Python format string, e.g. "cluster_domain: {cluster_domain}"

    def __init__(self):
        self.config = self.load_config()

    def build_content(self, cluster: Cluster) -> str:
        """Render the agent prompt for a single cluster."""
        return self.prompt_template.format(cluster_domain=cluster.immute_domain)

    @abstractmethod
    def load_config(self) -> BaseCheckConfig:
        """Return the config for this check type. Called once during __init__."""

    @abstractmethod
    def get_celery_task(self) -> Callable:
        """Return the bound Celery task function used to dispatch per-cluster work."""

    def _should_skip_simple(self, cluster: Cluster) -> tuple[bool, str]:
        """Cheap skip checks: age, phase, ignore list. No DB queries."""
        lookback_days = self.config.lookback_days
        now = timezone.now()

        if cluster.create_at > now - timedelta(days=lookback_days):
            return True, f"skipped: cluster younger than {lookback_days} days"

        if cluster.phase == ClusterPhase.OFFLINE.value:
            return True, "skipped: cluster offline"

        if cluster.immute_domain in self.config.ignore_cluster_domains:
            return True, "skipped: cluster in ignore list"

        return False, ""

    def should_skip(self, cluster: Cluster) -> tuple[bool, str]:
        """Skip clusters that are young, offline, in ignore list, or have recent/active tickets."""
        skipped, reason = self._should_skip_simple(cluster)
        if skipped:
            return True, reason

        cutoff = timezone.now() - timedelta(days=self.config.lookback_days)
        has_recent = (
            ClusterOperateRecord.objects.filter(
                cluster_id=cluster.id,
                ticket__ticket_type__in=REDIS_EXCLUSIVE_TICKET_TYPES,
            )
            .filter(Q(ticket__create_at__gte=cutoff) | Q(ticket__status__in=TICKET_RUNNING_STATUS_VALUES))
            .exists()
        )
        if has_recent:
            return True, "skipped: recent or active capacity/autofix/migrate ticket"

        return False, ""

    def get_clusters_to_check(self) -> list:
        """Fetch a batch of Redis clusters that have not been checked today for this subtype."""
        now = timezone.now()
        lookback_cutoff = now - timedelta(days=self.config.lookback_days)
        cluster_types = self.config.cluster_types or ClusterType.redis_cluster_types()

        # recently_checked_ids uses a Python set instead of a subquery because
        # RedisCheckReport and Cluster are on different databases.
        recently_checked_ids = set(
            RedisCheckReport.objects.filter(
                subtype=self.subtype.value,
                create_at__gte=now - timedelta(hours=24),
            ).values_list("cluster_id", flat=True)
        )

        cluster_qs = (
            Cluster.objects.filter(
                cluster_type__in=cluster_types,
                create_at__lte=lookback_cutoff,
            )
            .exclude(phase=ClusterPhase.OFFLINE.value)
            .exclude(id__in=recently_checked_ids)
        )
        if self.config.ignore_cluster_domains:
            cluster_qs = cluster_qs.exclude(immute_domain__in=self.config.ignore_cluster_domains)

        candidates = list(cluster_qs.order_by("id")[: self.config.batch_size * 2])

        if not candidates:
            return []

        busy_ids = set(
            ClusterOperateRecord.objects.filter(
                cluster_id__in=[c.id for c in candidates],
                ticket__ticket_type__in=REDIS_EXCLUSIVE_TICKET_TYPES,
            )
            .filter(Q(ticket__create_at__gte=lookback_cutoff) | Q(ticket__status__in=TICKET_RUNNING_STATUS_VALUES))
            .values_list("cluster_id", flat=True)
        )

        result = []
        for cluster in candidates:
            if len(result) >= self.config.batch_size:
                break
            if cluster.id not in busy_ids:
                result.append(cluster.id)

        return result

    def start(self) -> int:
        """Dispatch a batch of clusters for LLM analysis. Returns the number dispatched."""
        task_name = type(self).__name__

        if not self.config.enabled:
            logger.info("%s: disabled by config", task_name)
            return 0

        cluster_ids = self.get_clusters_to_check()
        if not cluster_ids:
            logger.debug("%s: no clusters to check", task_name)
            return 0

        celery_task = self.get_celery_task()
        dispatched = 0
        for cluster_id in cluster_ids:
            try:
                celery_task.apply_async(args=[cluster_id])
                dispatched += 1
            except Exception as e:
                logger.error("%s: failed to dispatch cluster_id=%s: %s", task_name, cluster_id, e)

        logger.info(
            "%s: dispatched %d clusters (sample ids=%s)",
            task_name,
            dispatched,
            cluster_ids[:5] if len(cluster_ids) >= 5 else cluster_ids,
        )
        return dispatched
