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
from dataclasses import dataclass, field, fields

from backend.configuration.constants import SystemSettingsEnum
from backend.db_meta.enums import ClusterType

logger = logging.getLogger("root")

DEFAULT_FULL_BACKUP_SCHEDULE_HOURS = {
    ClusterType.TendisRedisInstance.value: [5, 13, 21],
    ClusterType.TendisTwemproxyRedisInstance.value: [5, 13, 21],
    ClusterType.TendisPredixyRedisCluster.value: [5, 13, 21],
    ClusterType.TwemproxyTendisSSDInstance.value: [5],
    ClusterType.TendisPredixyTendisplusCluster.value: [5],
}


@dataclass
class RedisBackupCheckConfig:
    target_bk_cloud_ids: list = field(default_factory=lambda: [0])
    min_cluster_age_days: int = 2
    min_instance_age_hours: int = 48
    retention_days: int = 180
    ignore_domains: list = field(default_factory=list)
    full_backup_schedule_hours: dict = field(default_factory=lambda: dict(DEFAULT_FULL_BACKUP_SCHEDULE_HOURS))
    max_schedule_deviation_hours: float = 2.5

    def get_full_backup_schedule(self, cluster_type: str) -> list[int]:
        return self.full_backup_schedule_hours.get(
            cluster_type, DEFAULT_FULL_BACKUP_SCHEDULE_HOURS.get(cluster_type, [5])
        )

    @classmethod
    def from_raw(cls, raw: dict) -> "RedisBackupCheckConfig":
        valid_keys = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in valid_keys})

    @classmethod
    def from_settings(cls) -> "RedisBackupCheckConfig":
        from backend.configuration.models import SystemSettings

        raw = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_BACKUP_CHECK.value, default={})
        if not isinstance(raw, dict):
            if raw is not None:
                logger.warning("RedisBackupCheckConfig: expected dict, got %s", type(raw).__name__)
            return cls()
        return cls.from_raw(raw)
