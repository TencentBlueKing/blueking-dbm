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

from django.utils.translation import gettext_lazy as _

from backend import env
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.agent.handlers import AgentHandler

logger = logging.getLogger("celery.generate_mysql_skew_report")


# @register_periodic_task(run_every=crontab(minute=3, hour=2))
def generate_report():
    if not env.ENABLE_DBM_AI:
        logger.warning("ai not enabled")
        return

    for cluster_obj in Cluster.objects.filter(cluster_type__in=[ClusterType.TenDBHA, ClusterType.TenDBCluster]):
        AgentHandler.ask_agent_with_content(
            agent_code="ai-mysql-inspect",
            content=str(_("{} 生成最近 24 小时的集群倾斜报告".format(cluster_obj.immute_domain))),
            timeout=100,
        )
