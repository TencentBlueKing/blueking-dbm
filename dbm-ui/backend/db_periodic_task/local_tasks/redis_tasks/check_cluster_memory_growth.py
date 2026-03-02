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
from dataclasses import dataclass, field
from datetime import timedelta

from blueapps.core.celery.celery import app
from django.db.models import Q
from django.utils import timezone

import backend.dbm_aiagent.agent.commands as agent_commands
from backend.configuration.constants import DBType, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.models import RedisCheckReport
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
]


LOOKBACK_DAYS = 7


@dataclass
class ClusterMemoryGrowthCheckConfig:
    enabled: bool = False
    batch_size: int = 80  # amount of clusters to check each 10min
    ignore_cluster_domains: list = field(default_factory=list)

    @classmethod
    def from_settings(cls) -> "ClusterMemoryGrowthCheckConfig":
        raw = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_CLUSTER_MEMORY_GROWTH_CHECK.value, default={})
        if not isinstance(raw, dict):
            return cls()
        return cls(
            batch_size=raw.get("batch_size", 80),
            rate_limit=raw.get("rate_limit", "20/m"),
            min_cluster_age_days=raw.get("min_cluster_age_days", 7),
            ticket_lookback_days=raw.get("ticket_lookback_days", 7),
            lookback_days=raw.get("lookback_days", 7),
            ignore_cluster_domains=raw.get("ignore_cluster_domains", []),
        )


class CheckClusterMemoryGrowthTask:
    """Dispatcher for the Redis cluster memory growth LLM check.

    Reads config, selects unchecked clusters, and fans out per-cluster worker tasks.
    """

    def __init__(self):
        self.config = ClusterMemoryGrowthCheckConfig.from_settings()

    def should_skip(self, cluster: Cluster) -> tuple[bool, str]:
        """Skip clusters that are young, offline, in ignore list, or have recent/active tickets."""
        now = timezone.now()

        # Younger than N days
        if cluster.create_at > now - timedelta(days=LOOKBACK_DAYS):
            return True, f"skipped: cluster younger than {LOOKBACK_DAYS} days"

        # Offline
        if cluster.phase == ClusterPhase.OFFLINE.value:
            return True, "skipped: cluster offline"

        # In ignore list
        if cluster.immute_domain in self.config.ignore_cluster_domains:
            return True, "skipped: cluster in ignore list"

        # Recent or active tickets (capacity/autofix/migrate)
        cutoff = now - timedelta(days=LOOKBACK_DAYS)
        has_recent = (
            ClusterOperateRecord.objects.filter(
                cluster_id=cluster.id,
                ticket__ticket_type__in=REDIS_EXCLUSIVE_TICKET_TYPES,
            )
            .filter(
                Q(ticket__create_at__gte=cutoff) | Q(ticket__status__in=[s.value for s in TICKET_RUNNING_STATUS_SET])
            )
            .exists()
        )
        if has_recent:
            return True, "skipped: recent or active capacity/autofix/migrate ticket"

        return False, ""

    def get_clusters_to_check(self) -> list:
        """Fetch a batch of Redis clusters that have not been checked today."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        redis_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Redis.value)
        base_query = Q(cluster_type__in=redis_cluster_types) & Q(create_at__lt=timezone.now() - timedelta(hours=1))

        checked_today = set(
            RedisCheckReport.objects.filter(
                subtype=RedisCheckSubType.ClusterMemoryGrowth.value,
                create_at__gte=today_start,
            ).values_list("cluster_id", flat=True)
        )

        clusters = (
            Cluster.objects.filter(base_query)
            .exclude(id__in=checked_today)
            .order_by("id")[: self.config.batch_size * 2]
        )

        result = []
        for cluster in clusters:
            if len(result) >= self.config.batch_size:
                break
            skipped, _ = self.should_skip(cluster)
            if not skipped:
                result.append(cluster.id)

        return result

    def start(self) -> int:
        """Dispatch a batch of clusters for memory growth analysis. Returns the number dispatched."""
        if not self.config.enabled:
            logger.info("CheckClusterMemoryGrowthTask: disabled by config")
            return 0

        cluster_ids = self.get_clusters_to_check()
        if not cluster_ids:
            logger.debug("CheckClusterMemoryGrowthTask: no clusters to check")
            return 0

        dispatched = 0
        for cluster_id in cluster_ids:
            try:
                check_cluster_memory_growth_task.apply_async(args=[cluster_id])
                dispatched += 1
            except Exception as e:
                logger.error(
                    "CheckClusterMemoryGrowthTask: failed to dispatch cluster_id=%s: %s",
                    cluster_id,
                    e,
                )

        logger.info(
            "CheckClusterMemoryGrowthTask: dispatched %d clusters (sample ids=%s)",
            dispatched,
            cluster_ids[:5] if len(cluster_ids) >= 5 else cluster_ids,
        )
        return dispatched


@app.task(rate_limit="20/m")
def check_cluster_memory_growth_task(cluster_id: int):
    """
    Check a single Redis cluster's memory growth using LLM agent.

    The agent (ai-redis-memchk) queries metrics via MCP tools and creates the report.
    """
    try:
        cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            logger.warning("check_cluster_memory_growth_task: cluster_id=%s not found", cluster_id)
            return

        checker = CheckClusterMemoryGrowthTask()
        skipped, reason = checker.should_skip(cluster)
        if skipped:
            logger.debug(
                "check_cluster_memory_growth_task: cluster_id=%s skipped: %s",
                cluster_id,
                reason,
            )
            return

        from backend.dbm_aiagent.agent.handlers import AgentHandler

        AgentHandler.ask_agent_with_command(
            command=agent_commands.RedisMemoryGrowthAnalysisCommand.command,
            command_params={
                "cluster_domain": cluster.immute_domain,
            },
        )
        logger.info("check_cluster_memory_growth_task: cluster_id=%s done", cluster_id)

    except Exception as e:
        logger.exception(
            "check_cluster_memory_growth_task: cluster_id=%s failed: %s",
            cluster_id,
            e,
        )
