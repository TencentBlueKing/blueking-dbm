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
from typing import Callable

from blueapps.core.celery.celery import app

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base import BaseCheckConfig, BaseRedisAgentCheckTask
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.dbm_aiagent.agent.constants import DBMAgentCode

logger = logging.getLogger("root")


@dataclass
class BackendDataSkewCheckConfig(BaseCheckConfig):
    @classmethod
    def from_settings(cls) -> "BackendDataSkewCheckConfig":
        raw = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_BACKEND_DATA_SKEW_CHECK.value, default={})
        if not isinstance(raw, dict):
            return cls()
        return cls.from_raw(raw)


class CheckBackendDataSkewTask(BaseRedisAgentCheckTask):
    """Dispatcher for the Redis backend data skew LLM check."""

    subtype = RedisCheckSubType.BackendDataSkew
    agent_code = DBMAgentCode.REDIS_BACKEND_DATA_SKEW_CHECK
    prompt_template = "cluster_domain: {cluster_domain}"

    def load_config(self) -> BackendDataSkewCheckConfig:
        return BackendDataSkewCheckConfig.from_settings()

    def get_celery_task(self) -> Callable:
        return check_backend_data_skew_task


@app.task(rate_limit="10/m")
def check_backend_data_skew_task(cluster_id: int):
    """
    Check a single Redis cluster's backend data skew using LLM agent.

    The agent queries metrics via MCP tools and creates the report.
    """
    try:
        cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            logger.warning("check_backend_data_skew_task: cluster_id=%s not found", cluster_id)
            return

        checker = CheckBackendDataSkewTask()
        skipped, reason = checker.should_skip(cluster)
        if skipped:
            logger.debug(
                "check_backend_data_skew_task: cluster_id=%s skipped: %s",
                cluster_id,
                reason,
            )
            return

        from backend.dbm_aiagent.agent.handlers import AgentHandler

        AgentHandler.ask_agent_with_content(
            agent_code=checker.agent_code,
            content=checker.build_content(cluster),
        )
        logger.info("check_backend_data_skew_task: cluster_id=%s done", cluster_id)

    except Exception as e:
        logger.exception(
            "check_backend_data_skew_task: cluster_id=%s failed: %s",
            cluster_id,
            e,
        )
