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
        {% if query_digest_md5 is defined and query_digest_md5 %}
        根据提供的 query_digest_md5 值，查询原始 sql_text 文本，然后根据表结构和执行计划，进行分析优化:
        query_digest_md5: {{query_digest_md5}}
        {% else %}
        帮根据表结构和执行计划，我对以下 sql 进行优化:
        {{sql_text | default('', true)}}
        {% endif %}

        db集群 cluster_domain: {{cluster_domain}}
        {% if db_name is defined and db_name %}db 名 db_name: {{db_name}}{% endif %}
        """


@command
class MySQLSlowLogCommand(CommandHandler):
    name = _("查询慢日志")
    command = "query_slow_logs"
    agent_code = DBMAgentCode.MYSQL_SLOW_LOGS_QUERY

    def get_template(self) -> str:
        return """
        帮我分析集群 {{cluster_domain}} 的慢查询
        分析的时间窗口：'{{time_window_start}}' - '{{time_window_end}}'
        最大查询条数：{{limit}}
        instance_role: {{ instance_role}}
        只返回总结 Summary 部分的内容，具体 sql优化详情根据 skill 的指示存入 dbm 报告中心(markdown格式)返回链接即可。
        """


@command
class MySQLAlarmAnalyzerCommand(CommandHandler):
    name = _("告警分析")
    command = "alarm_analyzer"
    agent_code = DBMAgentCode.MYSQL_AI_INSPECT_AGENT

    def get_template(self) -> str:
        return """
        /mysql_alarm_analyzer 使用告警分析 skills 来分析告警，返回输出控制在 1800 字符以内。
        告警内容:
        {{alarm_content}}
        """


@command
class MySQLConfAnalyzeCommand(CommandHandler):
    name = _("mysql参数调优")
    command = "mysql_conf_analyze"
    agent_code = DBMAgentCode.MYSQL_CONFIG_PERF_TUNER

    def get_template(self) -> str:
        return """
        /mysql-config-optimization
        结合机器的规格，帮我分析集群 {{cluster_domain}} 的配置参数

        instance_role: {{ instance_role}}
        只返回总结 Summary 部分的内容，具体 sql优化详情根据 skill 的指示存入 dbm 报告中心(markdown格式)返回链接即可。
        所有返回输出控制在 1800 字符以内。
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
        是否过滤掉已屏蔽的告警记录：True
        告警级别过滤列表：[1]
        告警状态过滤列表：["ABNORMAL"]
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
        是否过滤掉已屏蔽的告警记录：True
        告警级别过滤列表：[1]
        告警状态过滤列表：["ABNORMAL"]
        """


@command
class RedisLatencyAlarmRootCauseCommand(CommandHandler):
    name = _("Redis 延迟告警归因分析")
    command = "redis_latency_alarm_root_cause"
    agent_code = DBMAgentCode.REDIS_REPORT

    def get_template(self) -> str:
        return """
        以下 Redis 集群发生了 L0 延迟告警，请帮我分析这批告警的关联性，判断是集群自身问题还是网络/机房等基础设施共性故障。

        ## 告警信息
        - 受影响集群列表：{{ cluster_domains }}

        ## 分析步骤
        1. 根据集群名查询每个集群的机器信息（机房、子Zone、交换机、云区域等）
        2. 对比各集群的机房/网络拓扑，判断是否集中在同一机房或共享同一交换机
        3. 结合告警时间是否集中，综合给出根因判断

        ## 输出格式
        **结论**：[孤立集群问题 / 单机房故障 / 交换机故障 / 跨机房网络抖动 / 其他基础设施问题]
        **置信度**：[高 / 中 / 低]
        **关键证据**：列出支撑结论的 2-3 条核心数据
        **建议排查方向**：针对结论给出具体的排查步骤

        返回输出控制在 800 字符以内。
        """


@command
class RedisPersistAnomalyRootCauseCommand(CommandHandler):
    name = _("Redis Persist 异常归因分析")
    command = "redis_persist_anomaly_root_cause"
    agent_code = DBMAgentCode.REDIS_REPORT

    def get_template(self) -> str:
        return """
        Redis 集群 {{ cluster_domain }} 发生了 Persist 异常告警，请帮我分析根因，重点判断是否为宿主机（母鸡）故障导致。

        ## 分析步骤
        1. 查询集群 {{ cluster_domain }} 的实例列表及所在宿主机信息
        2. 检查对应宿主机的健康状态（CPU、内存、磁盘 IO、系统告警等）
        3. 判断是宿主机故障导致的 Persist 异常，还是 Redis 实例自身的持久化问题

        ## 输出格式
        **结论**：[宿主机故障 / Redis 实例自身问题 / 磁盘 IO 瓶颈 / 其他]
        **置信度**：[高 / 中 / 低]
        **关键证据**：列出支撑结论的 2-3 条核心数据
        **建议排查方向**：针对结论给出具体的排查步骤

        返回输出控制在 800 字符以内。
        """


@command
class RedisSingleCpuHighRootCauseCommand(CommandHandler):
    name = _("Redis 单核 CPU 使用率归因分析")
    command = "redis_single_cpu_high_root_cause"
    agent_code = DBMAgentCode.REDIS_REPORT

    def get_template(self) -> str:
        return """
        Redis 集群 {{ cluster_domain }} 发生了单核 CPU 使用率过高告警，请帮我分析根因，重点判断是负载不均衡还是热 Key 导致。

        ## 分析步骤
        1. 查询集群 {{ cluster_domain }} 各实例的 CPU 使用情况，确认是哪个实例的单核 CPU 异常
        2. 检查该实例的热 Key 情况（访问频率最高的 Key、命令分布等）
        3. 对比同集群其他实例的 CPU 负载，判断是否存在负载不均衡（如 Slot 分布不均、主从流量差异等）
        4. 综合热 Key 和负载分布给出根因判断

        ## 输出格式
        **结论**：[热 Key 导致 / 负载不均衡 / 大 Key 操作 / 其他]
        **置信度**：[高 / 中 / 低]
        **关键证据**：列出支撑结论的 2-3 条核心数据
        **建议排查方向**：针对结论给出具体的排查步骤（如热 Key 打散、Slot 迁移、扩容等）

        返回输出控制在 800 字符以内。
        """
