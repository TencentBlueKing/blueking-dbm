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
from aidev_agent.services.command_handler import CommandHandler
from django.utils.translation import gettext as _

from ..constants import DBMAgentCode
from .register import command


@command
class CheckRedisClusterCommand(CommandHandler):
    name = _("查询单据运行期间这批Redis集群的是否存在风险性")
    command = "check_redis_cluster_operating_status"
    agent_code = DBMAgentCode.REDIS_TASK_GUARDIAN

    def get_template(self) -> str:
        return """
        查询单据运行期间这批Redis集群的是否存在风险性:
        业务ID：{{ bk_biz_id }}
        集群主域名列表：{{ cluster_domains }}
        查询起始时间点：{{ start_time }}
        查询截止时间点：{{ end_time }}
        """


@command
class GenRedisUpdReporterCommand(CommandHandler):
    name = _("生成Redis变更报告")
    command = "gen_redis_updater_report"
    agent_code = DBMAgentCode.REDIS_TASK_GUARDIAN

    def get_init(self) -> str:
        return "查询{{ cluster_domain }}集群部署情况"

    def get_report(self) -> str:
        return "再次查询{{ cluster_domain }}集群部署情况，并与上一次查询结果进行对比，生成变更报告"
