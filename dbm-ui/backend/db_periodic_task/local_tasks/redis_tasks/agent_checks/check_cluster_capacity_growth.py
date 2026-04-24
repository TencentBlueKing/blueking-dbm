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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import SystemSettingsEnum
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.base import (
    DEFAULT_AGENT_HARD_TIME_LIMIT_SECONDS,
    DEFAULT_AGENT_SOFT_TIME_LIMIT_SECONDS,
    BaseCheckConfig,
    BaseRedisAgentCheckTask,
    execute_agent_check,
)
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum

logger = logging.getLogger("root")

# Capacity-growth analysis is only meaningful when the cluster cannot evict
# data on its own. Any non-noeviction policy means Redis silently drops keys
# under memory pressure, so a "growing" working set is expected behavior and
# the LLM has nothing actionable to say. The dbconfig default is "noeviction"
# (see components/dbconfig/migrations/.../dbconf/Redis-*.json), so a missing
# value -- or any lookup failure -- conservatively keeps the cluster in scope.
MAXMEMORY_POLICY_CONF_NAME = "maxmemory-policy"
MAXMEMORY_POLICY_NOEVICTION = "noeviction"


def _query_maxmemory_policy(cluster: Cluster) -> str:
    """Return the cluster's effective ``maxmemory-policy`` from dbconfig.

    Empty string signals "unknown" to the caller (lookup returned nothing
    or the key is absent); the caller treats unknown as "do not skip".
    """
    data = DBConfigApi.query_conf_item(
        params={
            "bk_biz_id": str(cluster.bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": cluster.immute_domain,
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "conf_file": cluster.major_version,
            "conf_type": ConfigTypeEnum.DBConf,
            "namespace": cluster.cluster_type,
            "format": FormatType.MAP,
        }
    )
    content = (data or {}).get("content") or {}
    return str(content.get(MAXMEMORY_POLICY_CONF_NAME, "")).strip().lower()


@dataclass
class ClusterCapacityGrowthCheckConfig(BaseCheckConfig):
    setting_key: ClassVar[str] = SystemSettingsEnum.REDIS_CLUSTER_CAPACITY_GROWTH_CHECK.value


class CheckClusterCapacityGrowthTask(BaseRedisAgentCheckTask):
    """Dispatcher for the Redis cluster capacity growth LLM check."""

    subtype = RedisCheckSubType.ClusterCapacityGrowthRisk
    agent_code = DBMAgentCode.REDIS_CLUSTER_CAPACITY_GROWTH_CHECK
    prompt_template = "cluster_domains: [{cluster_domain}]"

    def load_config(self) -> ClusterCapacityGrowthCheckConfig:
        return ClusterCapacityGrowthCheckConfig.from_settings()

    def get_celery_task(self) -> Callable:
        return check_cluster_capacity_growth_task

    def extra_skip_check(self, cluster: Cluster) -> tuple[bool, str]:
        """Skip clusters whose maxmemory-policy enables eviction.

        Capacity-growth signal is meaningless when Redis evicts keys
        under pressure, so dispatching the LLM call would only burn
        quota. ``get_clusters_to_check`` runs this at dispatch time and
        catches any exception, so we don't need to add another safety
        layer here -- but unknown / absent policies fall through to "do
        not skip" because the dbconfig default is ``noeviction``.
        """
        policy = _query_maxmemory_policy(cluster)
        if not policy or policy == MAXMEMORY_POLICY_NOEVICTION:
            return False, ""
        return True, f"maxmemory-policy={policy} enables eviction"


# soft/hard limits below are a safety floor for direct invocations;
# ``start()`` overrides them per call from ``BaseCheckConfig``.
@app.task(
    bind=True,
    rate_limit="5/m",
    soft_time_limit=DEFAULT_AGENT_SOFT_TIME_LIMIT_SECONDS,
    time_limit=DEFAULT_AGENT_HARD_TIME_LIMIT_SECONDS,
)
def check_cluster_capacity_growth_task(self, cluster_id: int, config_dict: dict):
    """Check a single Redis cluster's capacity growth using LLM agent."""
    config = ClusterCapacityGrowthCheckConfig.from_raw(config_dict)
    execute_agent_check(
        agent_code=CheckClusterCapacityGrowthTask.agent_code,
        prompt_template=CheckClusterCapacityGrowthTask.prompt_template,
        config=config,
        cluster_id=cluster_id,
        celery_task=self,
    )
