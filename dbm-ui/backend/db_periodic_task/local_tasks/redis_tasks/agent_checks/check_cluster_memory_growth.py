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
from dataclasses import dataclass
from typing import Callable, ClassVar

from blueapps.core.celery.celery import app

from backend.configuration.constants import SystemSettingsEnum
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base import (
    BaseCheckConfig,
    BaseRedisAgentCheckTask,
    execute_agent_check,
)
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.dbm_aiagent.agent.constants import DBMAgentCode

logger = logging.getLogger("root")


@dataclass
class ClusterMemoryGrowthCheckConfig(BaseCheckConfig):
    setting_key: ClassVar[str] = SystemSettingsEnum.REDIS_CLUSTER_MEMORY_GROWTH_CHECK.value


class CheckClusterMemoryGrowthTask(BaseRedisAgentCheckTask):
    """Dispatcher for the Redis cluster memory growth LLM check."""

    subtype = RedisCheckSubType.ClusterMemoryCapacityRisk
    agent_code = DBMAgentCode.REDIS_MEMORY_GROWTH_ANALYSIS
    prompt_template = "cluster_domain: {cluster_domain}"

    def load_config(self) -> ClusterMemoryGrowthCheckConfig:
        return ClusterMemoryGrowthCheckConfig.from_settings()

    def get_celery_task(self) -> Callable:
        return check_cluster_memory_growth_task


@app.task(bind=True, rate_limit="5/m")
def check_cluster_memory_growth_task(self, cluster_id: int, config_dict: dict):
    """Check a single Redis cluster's memory growth using LLM agent."""
    config = ClusterMemoryGrowthCheckConfig.from_raw(config_dict)
    execute_agent_check(
        agent_code=CheckClusterMemoryGrowthTask.agent_code,
        prompt_template=CheckClusterMemoryGrowthTask.prompt_template,
        config=config,
        cluster_id=cluster_id,
        celery_task=self,
    )
