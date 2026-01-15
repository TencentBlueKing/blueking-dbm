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
class RenderExampleCommand(CommandHandler):
    name = _("渲染示例")
    command = "render"
    agent_code = DBMAgentCode.DBM

    def get_template(self) -> str:
        return """
        回答内容: {{ content }}
        请按照回答内容原样输出给用户回答
        """


@command
class TicketFlowLogAnalysisCommand(CommandHandler):
    name = _("单据日志分析")
    command = "ai-loganalysis"
    agent_code = DBMAgentCode.DBM

    def get_template(self) -> str:
        return """
        错误日志结构化信息：
        {{ log_content }}
        """
