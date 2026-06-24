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
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field, fields
from datetime import timedelta
from typing import List, Optional

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import SystemSettingsEnum
from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.models.redis_check_report import RedisCheckReport
from backend.flow.plugins.components.collections.redis.conf_check.registry import get_candidate_cluster_types
from backend.flow.utils.redis.redis_report_utils import RedisReportWriter
from backend.ticket.models import SystemSettings, TicketType
from backend.utils.basic import generate_root_id
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")


REDIS_CONF_CHECK_CANDIDATES_KEY = "dbm:redis_conf_check:candidates:{root_id}"
# TTL for candidates key in Redis (1 hour)
REDIS_CONF_CHECK_CANDIDATES_TTL = 3600
# Special field name for metadata in the hash
REDIS_CONF_CHECK_META_FIELD = "_meta"

# All conf checkers report under one subtype on RedisCheckReport.
CONF_CHECK_SUBTYPE = RedisCheckSubType.ConfigInconsistent.value


@dataclass
class RedisConfCheckConfig:
    """Configuration for the Redis conf check task."""

    enabled: bool = False
    bk_biz_id: int = 5005578  # The bk_biz_id the generated flow belongs to
    # Defaults to the union of all registered checkers' cluster types.
    cluster_types: Optional[List[str]] = field(default_factory=get_candidate_cluster_types)
    bizs_ignored: Optional[List[int]] = field(default_factory=list)
    clusters_ignored: Optional[List[int]] = field(default_factory=list)
    # Empty list means all cloud areas; when set (e.g. [0]), only check matching bk_cloud_id.
    bk_cloud_ids: Optional[List[int]] = field(default_factory=list)

    batch_size: int = 100  # amount of clusters to check each batch in flow
    batch_interval: int = 10  # sec to wait between batches
    interval: int = 10  # seconds between polls
    max_retries: int = 120  # timeout = interval * max_retries
    drs_chunk_size: int = 20  # amount of addresses per DRS redis_rpc call

    @classmethod
    def from_settings(cls) -> "RedisConfCheckConfig":
        """Load config from SystemSettings with dataclass defaults for missing keys."""
        raw = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_CONF_CHECK.value, default={})
        if not isinstance(raw, dict):
            if raw:
                logger.warning("RedisConfCheckConfig: expected dict, got %s", type(raw).__name__)
            return cls()

        valid_keys = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in valid_keys})

    def save_to_settings(self, user: str = "admin") -> None:
        """Persist this config to SystemSettings for shell_plus maintenance."""
        SystemSettings.insert_setting_value(
            key=SystemSettingsEnum.REDIS_CONF_CHECK.value,
            value=asdict(self),
            value_type="dict",
            user=user,
        )


def _get_config() -> RedisConfCheckConfig:
    """Read conf check configuration from SystemSettings (REDIS_CONF_CHECK)."""
    return RedisConfCheckConfig.from_settings()


def _get_candidate_clusters(config: RedisConfCheckConfig) -> List:
    """Return [(bk_cloud_id, cluster_id), ...] of online clusters of supported types."""
    query = Cluster.objects.filter(
        cluster_type__in=config.cluster_types,
        phase=ClusterPhase.ONLINE,
    )
    if config.bizs_ignored:
        query = query.exclude(bk_biz_id__in=config.bizs_ignored)
    if config.clusters_ignored:
        query = query.exclude(id__in=config.clusters_ignored)
    if config.bk_cloud_ids:
        query = query.filter(bk_cloud_id__in=config.bk_cloud_ids)
    return list(query.values_list("bk_cloud_id", "id"))


def check_redis_conf():
    """
    Main entry point for the unified Redis conf check.

    1. Read configuration from SystemSettings
    2. Select candidate clusters (union of all checkers' cluster types)
    3. Store candidates in a Redis Hash and trigger RedisConfCheckFlow
    4. Clean up expired reports
    """
    logger.info(_("Starting Redis conf check"))

    config = _get_config()
    if not config.enabled:
        logger.info(_("Redis conf check is disabled, exiting"))
        return

    cluster_tuples = _get_candidate_clusters(config)
    if not cluster_tuples:
        logger.info(_("No clusters found for conf check"))
        return

    logger.info(_("Found {} clusters for conf check").format(len(cluster_tuples)))

    cloud_to_clusters = defaultdict(list)
    for bk_cloud_id, cluster_id in cluster_tuples:
        cloud_to_clusters[bk_cloud_id].append(cluster_id)

    root_id = generate_root_id()
    candidates_key = REDIS_CONF_CHECK_CANDIDATES_KEY.format(root_id=root_id)
    try:
        hash_data = {
            str(bk_cloud_id): json.dumps(cluster_ids) for bk_cloud_id, cluster_ids in cloud_to_clusters.items()
        }
        hash_data[REDIS_CONF_CHECK_META_FIELD] = json.dumps(
            {
                "total_cloud_groups": len(cloud_to_clusters),
                "total_clusters": len(cluster_tuples),
                "created_at": root_id,
            }
        )
        RedisConn.hset(candidates_key, mapping=hash_data)
        RedisConn.expire(candidates_key, REDIS_CONF_CHECK_CANDIDATES_TTL)
        logger.info(
            _("Stored {} cloud groups ({} clusters) in Redis Hash: {}").format(
                len(cloud_to_clusters), len(cluster_tuples), candidates_key
            )
        )
    except Exception as e:
        logger.exception(_("Failed to store candidates in Redis: {}").format(str(e)))
        return

    flow_data = {
        "ticket_type": TicketType.REDIS_CONF_CHECK.value,
        "bk_biz_id": config.bk_biz_id,
        "created_by": "system",
        "candidates_key": candidates_key,
        "batch_size": config.batch_size,
        "batch_interval": config.batch_interval,
        "interval": config.interval,
        "max_retries": config.max_retries,
        "drs_chunk_size": config.drs_chunk_size,
    }

    try:
        # Lazy import to avoid circular import
        from backend.flow.engine.bamboo.scene.redis.redis_conf_check import RedisConfCheckFlow

        RedisConfCheckFlow(root_id, flow_data).run_flow()
        logger.info(_("Redis conf check flow started with root_id: {}").format(root_id))
    except Exception as e:
        logger.exception(_("Failed to start Redis conf check flow: {}").format(str(e)))

    writer = RedisReportWriter()
    cutoff = timezone.now() - timedelta(days=writer.retention_days)
    deleted_count, _detail = RedisCheckReport.objects.filter(subtype=CONF_CHECK_SUBTYPE, create_at__lt=cutoff).delete()
    logger.info(_("Deleted {} old conf check reports older than {} days").format(deleted_count, writer.retention_days))

    logger.info(_("Redis conf check completed"))
