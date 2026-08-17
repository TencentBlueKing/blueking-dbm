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
from dataclasses import asdict, dataclass, field, fields
from enum import StrEnum
from typing import List, Optional

from backend.configuration.constants import SystemSettingsEnum
from backend.ticket.builders.common.base import ClusterType
from backend.ticket.models import SystemSettings

logger = logging.getLogger("root")


class RedisRollbackExerciseMode(StrEnum):
    SPECIFIED = "specified"
    RANDOM = "random"


@dataclass
class RedisRollbackExerciseConfig:
    """
    Configuration of Redis rollback exericse.

    In SPECIFIED mode, ``specified_domains`` and ``specified_bizs`` combine as:
    - domains set, bizs unset: exercise every listed domain (legacy behavior).
    - domains set, bizs set: exercise only listed domains in those bizs.
    - domains unset, bizs set: discover ONLINE candidate clusters in those bizs.
    - domains unset, bizs unset: warn and skip.
    """

    # Meta Configs
    enabled: bool = False
    mode: RedisRollbackExerciseMode = RedisRollbackExerciseMode.RANDOM
    bk_biz_id: int = 0  # The biz where the drill ticket locates
    bk_cloud_ids: Optional[List[int]] = None  # Only exercise clusters in these cloud areas

    # Mode - Specifed
    specified_domains: Optional[List[str]] = None  # Customed targets [clusters]
    # Allowlist for SPECIFIED mode: filters specified_domains to clusters in these bizs;
    # when specified_domains is empty, discovers ONLINE clusters in these bizs instead.
    specified_bizs: Optional[List[int]] = None

    # Mode - Random
    batch_size: int = 2000  # Count of clusters to exercise each week
    bizs_high_priority: Optional[List[int]] = None  # Customed bizs with high priority
    clusters_ignored: Optional[List[int]] = None  # Customed clusters(id) to ignore
    bizs_ignored: Optional[List[int]] = None  # Customed bizs to ignore
    cluster_types: List[str] = field(
        default_factory=lambda: [
            ClusterType.TendisTwemproxyRedisInstance.value,  # TendisCache 集群
            ClusterType.TwemproxyTendisSSDInstance.value,  # TendisSSD 集群
            ClusterType.TendisRedisInstance.value,  # Redis 主从
            ClusterType.TendisPredixyRedisCluster.value,
            ClusterType.TendisPredixyTendisplusCluster.value,
        ]
    )  # Customed ClusterTypes to exercise

    # Weighted selection: probability multipliers (how many times more likely to be selected)
    # Combined effect is multiplicative, e.g., high_priority + failed = 2.0 * 3.0 = 6x more likely
    weight_multiplier_high_priority_biz: float = 2.0  # 2x more likely than default
    weight_multiplier_previously_failed: float = 3.0  # 3x more likely than default
    weight_multiplier_not_exercised: float = 2.0  # 2x more likely for clusters not exercised recently
    not_exercised_days_threshold: int = 180  # Days threshold for "not exercised" status

    # Error handling
    # False (default): on child failure/timeout, stop and keep the scene
    # (temp instances and child pipelines stay) until DBA skips the node; then mark failed and clean up.
    # True: legacy behavior — continue and clean up immediately.
    error_ignorable: bool = False
    # Alarm-shield duration (minutes) while the scene is preserved, so temp instances stay quiet.
    preserve_scene_shield_minutes: int = 4320

    # Extra
    max_instances: int = 10  # Each round
    rollback_days: List[int] = field(default_factory=lambda: [0.1, 0.2, 0.3, 0.4, 0.5, 1, 2])  # Rollback days
    polling_interval: int = 10  # sec
    polling_timeout: int = 3600  # sec

    # AI failure analysis / weekly digest (also requires env.ENABLE_DBM_AI)
    ai_analysis_enabled: bool = False

    # Recovery time-point offset (after the chosen full backup uptime).
    # SSD / Tendisplus default ~23h50m so we exercise almost a full day of binlog
    # (daily full backup at ~05:00 -> rollback target lands ~04:50 of next day,
    # safely before the next full backup window).
    binlog_replay_minutes: int = 1430
    # Cluster types without binlog (cache / redis main-slave / predixy redis cluster)
    # only need a small offset past the full backup uptime.
    no_binlog_offset_minutes: int = 30

    @classmethod
    def from_settings(cls) -> "RedisRollbackExerciseConfig":
        """Load config from SystemSettings with dataclass defaults for missing keys."""
        raw = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_ROLLBACK_EXERCISE.value, default={})
        if not isinstance(raw, dict):
            if raw:
                logger.warning("RedisRollbackExerciseConfig: expected dict, got %s", type(raw).__name__)
            return cls()

        valid_keys = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in valid_keys})

    def save_to_settings(self, user: str = "admin") -> None:
        """Persist this config to SystemSettings for shell_plus maintenance."""
        SystemSettings.insert_setting_value(
            key=SystemSettingsEnum.REDIS_ROLLBACK_EXERCISE.value,
            value=asdict(self),
            value_type="dict",
            user=user,
        )
