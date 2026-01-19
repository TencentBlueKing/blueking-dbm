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
    command = "LogAnalysis"
    # 现在都是走主智能体路由，所以agent code都是dbm
    agent_code = DBMAgentCode.DBM

    def get_template(self) -> str:
        return """
        单据类型：{{ ticket_type }}
        错误日志信息：{{ log_content }}
        """


@command
class MysqlSlowSqlTunerCommand(CommandHandler):
    name = _("MySQL慢SQL调优")
    command = "sql-tuner"
    agent_code = DBMAgentCode.MYSQL_SLOW_LOGS_QUERY

    def get_template(self) -> str:
        return """
        {% if query_digest_md5 %}
        根据提供的 query_digest_md5 值，查询原始 sql_text 文本，然后根据表结构和执行计划，进行分析优化:
        query_digest_md5: {{query_digest_md5}}
        {% else %}
        帮根据表结构和执行计划，我对以下 sql 进行优化:
        {{sql_text}}
        {% endif %}

        业务ID bk_biz_id: {{bk_biz_id}}
        db集群 cluster_domain: {{cluster_domain}}
        db 名 db_name: {{db_name}} (如果有)
        """


@command
class CheckMysqlClusterCommand(CommandHandler):
    name = _("查询单据运行期间这批MySQL集群的是否存在风险性")
    command = "check_mysql_cluster_operating_status"
    agent_code = DBMAgentCode.MYSQL_TASK_GUARDIAN

    def get_template(self) -> str:
        return """
        查询单据运行期间这批MySQL集群的是否存在风险性:
        业务ID：{{ bk_biz_id }}
        集群主域名列表：{{ cluster_domains }}
        查询起始时间点：{{ start_time }}
        查询截止时间点：{{ end_time }}
        """


@command
class CheckSQLServerClusterCommand(CommandHandler):
    name = _("查询单据运行期间这批SQLServer集群的是否存在风险性")
    command = "check_sqlserver_cluster_operating_status"
    agent_code = DBMAgentCode.SQLSERVER_TASK_GUARDIAN

    def get_template(self) -> str:
        return """
        查询单据运行期间这批SQLServer集群的是否存在风险性:
        业务ID：{{ bk_biz_id }}
        集群主域名列表：{{ cluster_domains }}
        查询起始时间点：{{ start_time }}
        查询截止时间点：{{ end_time }}
        """
