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
from dataclasses import dataclass, field
from typing import ClassVar

from django.core.exceptions import ValidationError

from backend.dbm_aiagent.tasks.config import AITaskConfig, IdempotenceMode

REDIS_AGENT_CHECK_MAX_PRODUCE_BATCH_SIZE = 2000
DEFAULT_LOOKBACK_DAYS = 7
# Marks a producer-side NORMAL report written instead of dispatching a check.
SKIP_REPORT_MSG_PREFIX = "skipped:"


@dataclass
class RedisAgentCheckConfig(AITaskConfig):
    """Redis agent-check selection and skip configuration.

    Each concrete check owns a ``DispatchTaskSettings`` row identified by its
    ``task_key`` in the ``ai`` queue.
    """

    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ignore_cluster_domains: list[str] = field(default_factory=list)
    cluster_types: list[str] = field(default_factory=list)
    candidate_page_size: int = 200
    max_candidate_scan: int = 0
    recent_check_mode: str = "calendar_day"
    normal_skip_days: float = 0
    priority_alarm_names: list[str] = field(default_factory=list)
    priority_alarm_lookback_hours: int = 24 * 30
    priority_alarm_request_name_filter: bool = False

    # Rotation top-up only when this task's pending is below this watermark.
    produce_low_watermark: int = 200
    # Top-up until pending ≈ target; per-run rotation cap = target - pending.
    produce_target_pending: int = 500
    # Spread rotation ready_at over this window (seconds); 0 = enqueue at now.
    produce_spread_window_seconds: int = 0
    # Priority (alarm) jobs use ready_at = now - lead to jump the pending queue.
    priority_execute_lead_seconds: int = 300

    @classmethod
    def validate_raw(cls, raw: dict) -> None:
        super().validate_raw(raw)
        config = cls.from_raw(raw)
        positive_fields = (
            "lookback_days",
            "candidate_page_size",
            "priority_alarm_lookback_hours",
            "produce_low_watermark",
            "produce_target_pending",
        )
        for name in positive_fields:
            if getattr(config, name) < 1:
                raise ValidationError({"config": f"{name} must be at least 1"})
        non_negative_fields = (
            "max_candidate_scan",
            "normal_skip_days",
            "produce_spread_window_seconds",
            "priority_execute_lead_seconds",
        )
        for name in non_negative_fields:
            if getattr(config, name) < 0:
                raise ValidationError({"config": f"{name} cannot be negative"})
        if config.produce_target_pending < config.produce_low_watermark:
            raise ValidationError({"config": "produce_target_pending must be at least produce_low_watermark"})
        if config.produce_target_pending > REDIS_AGENT_CHECK_MAX_PRODUCE_BATCH_SIZE:
            raise ValidationError(
                {"config": ("produce_target_pending cannot exceed " f"{REDIS_AGENT_CHECK_MAX_PRODUCE_BATCH_SIZE}")}
            )


@dataclass
class BackendDataSkewCheckConfig(RedisAgentCheckConfig):
    task_key: ClassVar[str] = "redis.backend_data_skew"
    idempotence_mode: IdempotenceMode = IdempotenceMode.DEDUPE


@dataclass
class BackendLoadSkewCheckConfig(RedisAgentCheckConfig):
    task_key: ClassVar[str] = "redis.backend_load_skew"
    idempotence_mode: IdempotenceMode = IdempotenceMode.DEDUPE


@dataclass
class ClusterCapacityGrowthCheckConfig(RedisAgentCheckConfig):
    task_key: ClassVar[str] = "redis.cluster_capacity_growth"
    idempotence_mode: IdempotenceMode = IdempotenceMode.DEDUPE
