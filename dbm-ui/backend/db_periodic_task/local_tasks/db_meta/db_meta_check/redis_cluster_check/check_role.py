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
from dataclasses import dataclass, field
from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import SystemSettingsEnum
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType
from backend.flow.utils.redis.redis_meta_report import delete_old_meta_check_reports
from backend.ticket.models import SystemSettings
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


# Default supported cluster types for role check
DEFAULT_CLUSTER_TYPES = [
    ClusterType.TendisPredixyRedisCluster.value,
    ClusterType.TendisPredixyTendisplusCluster.value,
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisRedisInstance.value,
]


@dataclass
class RedisRoleCheckConfig:
    """
    Configuration for Redis role check task
    """

    switch: bool = False
    bk_biz_id: int = 5005578  # The bk_biz_id the generated flow belongs to
    cluster_types: Optional[List[str]] = field(default_factory=lambda: DEFAULT_CLUSTER_TYPES)
    bizs_ignored: Optional[List[int]] = field(default_factory=list)
    clusters_ignored: Optional[List[int]] = field(default_factory=list)

    batch_size: int = 1000  # amount of clusters to check each batch in flow
    interval = 5  # seconds
    max_retries = 120  # timeout = interval * max_retries


def _get_config() -> RedisRoleCheckConfig:
    """
    Read and parse role check configuration from SystemSettings
    """
    config_dict = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_ROLE_CHECK.value, {})
    return RedisRoleCheckConfig(**config_dict)


def _get_candidate_clusters(config: RedisRoleCheckConfig) -> List[int]:
    """
    Get candidate clusters for role check based on configuration

    Args:
        config: Role check configuration

    Returns:
        List of cluster_id and bk_could_id
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

    query = query.values_list("bk_could_id", "id")

    return list(query)


def check_redis_instance_role():
    """
    Main entry point for Redis instance role check

    This function:
    1. Reads configuration from SystemSettings
    2. Gets candidate clusters based on config
    3. Prepares cluster info and triggers RedisRoleCheckFlow
    """
    logger.info(_("Starting Redis instance role check"))

    # Read configuration
    config = _get_config()

    if not config.switch:
        logger.info(_("Redis role check is disabled, exiting"))
        return

    # Get candidate clusters: list of (bk_cloud_id, cluster_id) tuples
    cluster_tuples = _get_candidate_clusters(config)

    if not cluster_tuples:
        logger.info(_("No clusters found for role check"))
        return

    logger.info(_("Found {} clusters for role check").format(len(cluster_tuples)))

    # Prepare infos: group clusters by bk_cloud_id
    cloud_to_clusters = defaultdict(list)
    for bk_cloud_id, cluster_id in cluster_tuples:
        cloud_to_clusters[bk_cloud_id].append(cluster_id)
    infos = [
        {"bk_cloud_id": bk_cloud_id, "cluster_ids": cluster_ids}
        for bk_cloud_id, cluster_ids in cloud_to_clusters.items()
    ]

    if not infos:
        logger.warning(_("No valid clusters prepared for role check"))
        return

    logger.info(
        _("Prepared {} cloud groups with {} total clusters for role check flow").format(
            len(infos), len(cluster_tuples)
        )
    )

    # Generate a unique root_id for this check run
    root_id = generate_root_id()

    # Build flow data
    flow_data = {
        "ticket_type": "REDIS_ROLE_CHECK",
        "bk_biz_id": config.bk_biz_id,
        "created_by": "system",
        "infos": infos,
        "batch_size": config.batch_size,
        "interval": config.interval,
        "max_retries": config.max_retries,
    }

    try:
        # Lazy import to avoid circular import
        from backend.flow.engine.bamboo.scene.redis.redis_role_check import RedisRoleCheckFlow

        RedisRoleCheckFlow(root_id, flow_data).run_flow()
        logger.info(_("Redis role check flow started with root_id: {}").format(root_id))
    except Exception as e:
        logger.exception(_("Failed to start Redis role check flow: {}").format(str(e)))

    delete_old_meta_check_reports(MetaCheckSubType.RoleMismatch, config.cluster_types, days=30)

    logger.info(_("Redis instance role check completed"))
