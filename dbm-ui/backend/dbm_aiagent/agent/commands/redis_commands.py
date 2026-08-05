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


@command
class CheckRedisIpCommand(CommandHandler):
    name = _("Redis IP快捷查询")
    command = "query_redis_host_info"
    agent_code = DBMAgentCode.REDIS_HELPER

    def get_template(self) -> str:
        return """
        查询这批{{ ips }}机器的所属集群、角色，并看下所属集群的 Proxy层的QPS、Proxy层连接数情况
        """


@command
class RedisBackendLoadSkewCheck(CommandHandler):
    name = _("Redis后端负载倾斜检查")
    command = "RedisBackendLoadSkewCheck"
    agent_code = DBMAgentCode.REDIS_METRICS

    def get_template(self) -> str:
        return """
        cluster_domains: [{{ cluster_domain }}]
        """


@command
class RedisClusterMemoryGrowthAnalysis(CommandHandler):
    name = _("Redis集群内存增长分析")
    command = "RedisClusterMemoryGrowthAnalysis"
    agent_code = DBMAgentCode.REDIS_METRICS

    def get_template(self) -> str:
        return """
        cluster_domains: [{{ cluster_domain }}]
        """


@command
class AnalyzeRedisRollbackExerciseFailure(CommandHandler):
    name = _("分析Redis回档演练失败")
    command = "AnalyzeRedisRollbackExerciseFailure"
    agent_code = DBMAgentCode.REDIS_EXERCISE_ANALYST

    def get_template(self) -> str:
        return """
        /redis-rollback-exercise-analyst 使用回档演练分析 skill 来诊断本次失败，给出简短诊断。

        集群域名：{{ cluster_domain }}
        集群类型：{{ cluster_type }}
        实例：{{ instance }}
        版本：{{ redis_version }}
        失败阶段：{{ task_stage }}

        报告任务日志(task_message，回档/清理失败时已内嵌[子流程失败节点日志]块)：
        {{ task_message }}

        输出要求（严格遵守，总长度控制在 4 行以内）：
        1. 第一行必须是：原因分类: <类别>
           类别只能从以下取值其一：备份不可用 / 单据生成失败 / 资源申请失败 / 构造流程失败 / 清理失败 / 轮询超时 / 执行器错误 / 环境跳过残留 / 其他
        2. 第二行：诊断: <一句话，必须有日志证据，禁止臆测>
        3. 第三行：建议: <一条可执行下一步>
        4. 不要输出 markdown 标题、代码块或多余解释。
        """


@command
class SummarizeRedisRollbackExerciseWeek(CommandHandler):
    name = _("汇总Redis回档演练周报")
    command = "SummarizeRedisRollbackExerciseWeek"
    agent_code = DBMAgentCode.REDIS_EXERCISE_ANALYST

    def get_template(self) -> str:
        return """
        /redis-rollback-exercise-analyst 使用回档演练分析 skill 的周报输出约定来汇总本周演练。
        下面的统计数字已由系统确定性计算，请直接采信，不要重新计数。

        统计窗口：{{ window }}

        统计 JSON：
        {{ stats_json }}

        代表性失败样例（每行：域名 实例 阶段 原因分类 | 诊断）：
        {{ failure_cases }}

        请输出中文 Markdown 周报，包含且仅包含以下章节：
        1. 概览（总量、成功率、失败/跳过、相对上周变化）
        2. 失败原因分布（基于 stats 中的 category 计数）
        3. 失败阶段分布
        4. 重复失败集群
        5. 典型失败样例（从上方样例挑选 3-8 个有代表性的，引用其分类与诊断，同因合并；禁止编造样例之外的案例）

        要求：简洁、可执行、不要编造 stats 中没有的数字。
        """
