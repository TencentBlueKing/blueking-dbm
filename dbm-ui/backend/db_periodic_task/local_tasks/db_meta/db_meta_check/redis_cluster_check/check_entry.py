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
from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import SystemSettingsEnum
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType
from backend.flow.utils.redis.redis_meta_report import delete_old_meta_check_reports
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models import ClusterOperateRecord, SystemSettings
from backend.utils.basic import generate_root_id
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")


REDIS_ENTRY_CHECK_CANDIDATES_KEY = "dbm:redis_entry_check:candidates:{root_id}"
# TTL for candidates key in Redis (1 hour)
REDIS_ENTRY_CHECK_CANDIDATES_TTL = 3600


# Default supported cluster types for entry check
DEFAULT_CLUSTER_TYPES = [
    ClusterType.TendisPredixyRedisCluster.value,
    ClusterType.TendisPredixyTendisplusCluster.value,
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TwemproxyTendisSSDInstance.value,
]

# Ticket types that involve proxy changes - clusters with these active tickets should be skipped
PROXY_CHANGE_TICKET_TYPES = [
    TicketType.REDIS_PROXY_SCALE_UP.value,
    TicketType.REDIS_PROXY_SCALE_DOWN.value,
    TicketType.REDIS_PROXY_OPEN.value,
    TicketType.REDIS_PROXY_CLOSE.value,
    TicketType.REDIS_CLUSTER_AUTOFIX.value,
]


@dataclass
class RedisEntryCheckConfig:
    """
    Configuration for Redis entry check task
    """

    enabled: bool = False
    bk_biz_id: int = 5005578  # The bk_biz_id the generated flow belongs to
    cluster_types: Optional[List[str]] = field(default_factory=lambda: DEFAULT_CLUSTER_TYPES)
    bizs_ignored: Optional[List[int]] = field(default_factory=list)
    clusters_ignored: Optional[List[int]] = field(default_factory=list)

    batch_size: int = 100  # amount of clusters to check each batch in flow
    batch_interval: int = 10  # sec to wait between batches


def _get_config() -> RedisEntryCheckConfig:
    """
    Read and parse entry check configuration from SystemSettings
    """
    config_dict = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_ENTRY_CHECK.value, {})
    return RedisEntryCheckConfig(**config_dict)


def _get_candidate_clusters(config: RedisEntryCheckConfig) -> List[int]:
    """
    Get candidate clusters for entry check based on configuration

    Args:
        config: Entry check configuration

    Returns:
        List of cluster_ids
    """
    # Base query: online clusters of supported types
    query = Cluster.objects.filter(
        cluster_type__in=config.cluster_types,
        phase=ClusterPhase.ONLINE,
    )

    # Exclude ignored bizs and clusters
    if config.bizs_ignored:
        query = query.exclude(bk_biz_id__in=config.bizs_ignored)

    if config.clusters_ignored:
        query = query.exclude(id__in=config.clusters_ignored)

    # Get cluster IDs first
    cluster_ids = list(query.values_list("id", flat=True))

    # Filter out clusters with active proxy-change tickets
    clusters_with_active_tickets = set(
        ClusterOperateRecord.objects.filter(
            ticket__ticket_type__in=PROXY_CHANGE_TICKET_TYPES,
            ticket__status__in=TICKET_RUNNING_STATUS_SET,
            cluster_id__in=cluster_ids,
        ).values_list("cluster_id", flat=True)
    )

    if clusters_with_active_tickets:
        logger.info(
            _("Excluding {} clusters with active proxy-change tickets").format(len(clusters_with_active_tickets))
        )

    # Filter out clusters with active tickets
    filtered_cluster_ids = [cid for cid in cluster_ids if cid not in clusters_with_active_tickets]

    return filtered_cluster_ids


def check_redis_entry_consistency():
    """
    Main entry point for Redis entry consistency check

    This function:
    1. Reads configuration from SystemSettings
    2. Gets candidate clusters based on config
    3. Prepares cluster info and triggers RedisEntryCheckFlow for batch processing
    """
    logger.info(_("Starting Redis entry consistency check"))

    # Read configuration
    config = _get_config()

    if not config.enabled:
        logger.info(_("Redis entry check is disabled, exiting"))
        return

    # Get candidate clusters: list of cluster_ids
    cluster_ids = _get_candidate_clusters(config)

    if not cluster_ids:
        logger.info(_("No clusters found for entry check"))
        return

    logger.info(_("Found {} clusters for entry check").format(len(cluster_ids)))

    # Generate a unique root_id for this check run
    root_id = generate_root_id()

    candidates_key = REDIS_ENTRY_CHECK_CANDIDATES_KEY.format(root_id=root_id)
    try:
        # Store cluster_ids as a Redis list using LPUSH
        # Push all cluster_ids to the list
        if cluster_ids:
            RedisConn.lpush(candidates_key, *cluster_ids)
            RedisConn.expire(candidates_key, REDIS_ENTRY_CHECK_CANDIDATES_TTL)

        logger.info(_("Stored {} clusters in Redis list: {}").format(len(cluster_ids), candidates_key))
    except Exception as e:
        logger.exception(_("Failed to store candidates in Redis: {}").format(str(e)))
        return

    # Build flow data - using candidates_key instead of infos to prevent large flow data
    flow_data = {
        "ticket_type": TicketType.REDIS_ENTRY_CHECK.value,
        "bk_biz_id": config.bk_biz_id,
        "created_by": "system",
        "candidates_key": candidates_key,
        "batch_size": config.batch_size,
        "batch_interval": config.batch_interval,
    }

    try:
        # Lazy import to avoid circular import
        from backend.flow.engine.bamboo.scene.redis.redis_entry_check import RedisEntryCheckFlow

        RedisEntryCheckFlow(root_id, flow_data).run_flow()
        logger.info(_("Redis entry check flow started with root_id: {}").format(root_id))
    except Exception as e:
        logger.exception(_("Failed to start Redis entry check flow: {}").format(str(e)))

    delete_old_meta_check_reports(MetaCheckSubType.EntryInconsistent, config.cluster_types, days=30)

    logger.info(_("Redis entry consistency triggered."))
