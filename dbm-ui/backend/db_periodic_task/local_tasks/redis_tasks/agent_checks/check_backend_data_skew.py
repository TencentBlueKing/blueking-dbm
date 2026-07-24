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
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config import BackendDataSkewCheckConfig
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.redis_adapter import RedisAgentCheckTask
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.tasks.registry import ai_task


@ai_task(
    agent_code=DBMAgentCode.REDIS_BACKEND_DATA_SKEW_CHECK,
    config_cls=BackendDataSkewCheckConfig,
    db_type="redis",
)
class CheckBackendDataSkewTask(RedisAgentCheckTask):
    """Dispatcher for the Redis backend data skew LLM check."""

    subtype = RedisCheckSubType.BackendDataSkew
    prompt_template = "cluster_domains: [{cluster_domain}]"
