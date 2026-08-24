"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
import random
import re
import time

from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

import backend.dbm_aiagent.agent.commands as commands
from backend.configuration.constants import DBType
from backend.core import notify
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.flow.models import FlowTree, FlowWithAITaskGuardianReport
from backend.flow.plugins.components.collections.common.sidecar_service_abc import SidecarServiceABC
from backend.utils.time import datetime2str

cpl = re.compile(r"\[ai_result]\s*(?P<context>.+?)\s*\[ai_result]", re.DOTALL)

# 定义不同DB组件调用对应的智能体快捷指令的MAP
ASK_AI_COMMAND_MAP = {
    DBType.MySQL: commands.CheckMysqlClusterCommand,
    DBType.TenDBCluster: commands.CheckMysqlClusterCommand,
    DBType.Sqlserver: commands.CheckSQLServerClusterCommand,
    DBType.Redis: commands.CheckRedisClusterCommand,
    DBType.Kafka: commands.CheckKafkaClusterCommand,
    DBType.Es: commands.CheckEsClusterCommand,
    DBType.MongoDB: commands.CheckMongoDBClusterCommand,
    DBType.Pulsar: commands.CheckPulsarClusterCommand,
    DBType.Hdfs: commands.CheckHdfsClusterCommand,
    DBType.Doris: commands.CheckDorisClusterCommand,
}

# 定义不同DB组件对应的单据值守智能体代码MAP（用于风险报告语义比对等场景）
TASK_GUARDIAN_AGENT_MAP = {
    DBType.MySQL: DBMAgentCode.MYSQL_TASK_GUARDIAN,
    DBType.TenDBCluster: DBMAgentCode.MYSQL_TASK_GUARDIAN,
    DBType.Sqlserver: DBMAgentCode.SQLSERVER_TASK_GUARDIAN,
    DBType.Redis: DBMAgentCode.REDIS_TASK_GUARDIAN,
    DBType.Kafka: DBMAgentCode.KAFKA_TASK_GUARDIAN,
    DBType.Es: DBMAgentCode.ES_TASK_GUARDIAN,
    DBType.MongoDB: DBMAgentCode.MONGO_TASK_GUARDIAN,
    DBType.Pulsar: DBMAgentCode.PULSAR_TASK_GUARDIAN,
    DBType.Hdfs: DBMAgentCode.HDFS_TASK_GUARDIAN,
    DBType.Doris: DBMAgentCode.DORIS_TASK_GUARDIAN,
}


class CheckClusterAlarmForAIService(SidecarServiceABC):
    """
    定义单据值守通用的component
    检查单据运行期间，通过AI方式计算出对应集群信息，所产生的告警记录
    收集到告警记录，推送给DBA+提单者

    支持消息推送收敛：
        - 指数退避：推送频率递减，避免持续问题造成消息轰炸
        - 风险等级升级打破沉默：风险加剧时立即推送
        - AI语义比对打破沉默：通过智能体比对前后两次风险报告，出现新风险点时立即推送
        - 风险恢复重置：连续无风险后重置退避计数器
        - 收敛开关：支持按单据维度关闭收敛

    Attributes:
        interval: 轮询间隔时间生成器，每30秒执行一次检查
    """

    interval = StaticIntervalGenerator(30)

    @staticmethod
    def _get_or_create_report(root_id: str, uid: str, enable_converge: bool) -> FlowWithAITaskGuardianReport:
        """
        获取或创建推送收敛记录

        Args:
            root_id: 流程ID
            uid: 单据ID
            enable_converge: 是否启用收敛

        Returns:
            FlowWithAITaskGuardianReport 实例
        """
        report, created = FlowWithAITaskGuardianReport.objects.get_or_create(
            root_id=root_id,
            uid=uid,
            defaults={"enable_converge": enable_converge},
        )
        # 如果记录已存在但收敛开关状态有变化，则更新
        if not created and report.enable_converge != enable_converge:
            report.enable_converge = enable_converge
            report.save(update_fields=["enable_converge"])
        return report

    @staticmethod
    def _extract_risk_level(ai_result_info: dict) -> str:
        """
        从AI返回的结构化结果中提取风险等级，兼容字段缺失

        Args:
            ai_result_info: AI返回的结构化结果字典

        Returns:
            风险等级字符串，未返回则为空字符串
        """
        return ai_result_info.get("risk_level", "")

    @staticmethod
    def _clean_ai_result_tags(ai_result: str) -> str:
        """
        清理AI返回文本中的 [ai_result]...[ai_result] 标签，只保留分析报告正文

        Args:
            ai_result: AI原始返回文本

        Returns:
            清理后的纯文本
        """
        return re.sub(r"\[ai_result]\s*\{.*?}\s*\[ai_result]", "", ai_result, flags=re.DOTALL).strip()

    @staticmethod
    def _compare_reports_with_ai(last_report: str, current_report: str, db_type: DBType) -> bool:
        """
        调用智能体语义比对两份风险报告，判断是否为同一风险

        相比 MD5 指纹方案，AI 语义比对能正确处理：
            - "CPU高" vs "CPU很高" → 同一风险 ✅
            - "CPU负载高" vs "磁盘空间不足" → 不同风险 ✅

        Args:
            last_report: 上一次推送的风险报告内容
            current_report: 本次的风险报告内容
            db_type: DB组件类型，用于选择对应的单据值守智能体

        Returns:
            bool: True=同一风险（应收敛），False=不同风险（应推送）
                  比对失败时返回 False（保守策略，允许推送）
        """
        # 如果上次报告为空，无法比对，视为不同风险
        if not last_report:
            return False

        # 延迟导入: AgentHandler 依赖的 aidev_bkplugin 仅在 ENABLE_DBM_AI=true 时进入 INSTALLED_APPS
        from backend.dbm_aiagent.agent.handlers import AgentHandler

        # 根据DB组件类型选择对应的单据值守智能体，未匹配则使用通用单据值守智能体
        agent_code = TASK_GUARDIAN_AGENT_MAP.get(db_type, DBMAgentCode.TASK_GUARDIAN)

        result = AgentHandler.compare_risk_reports(
            last_report=last_report,
            current_report=current_report,
            agent_code=agent_code,
        )
        return result.get("is_same_risk", False) if result else False

    def _prepare_context(self, data, parent_data) -> dict | None:
        """
        准备sidecar执行所需的上下文数据

        Args:
            data: Pipeline数据对象
            parent_data: Pipeline父节点数据对象

        Returns:
            dict: 包含所有上下文信息的字典，如果集群为空则返回 None
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        cluster_ids = kwargs["cluster_ids"]
        enable_converge = kwargs.get("enable_converge", True)
        root_id = global_data["job_root_id"]
        flow_tree = FlowTree.objects.get(root_id=root_id)
        now_time = timezone.now()

        # 判断uid的变量正确性
        try:
            ticket_id = int(flow_tree.uid)
        except (TypeError, ValueError):
            self.log_error(_("查询到flow对应的单据ID不合法，请检查flow的单据信息。uid：{}".format(flow_tree.uid)))
            return None

        clusters = Cluster.objects.filter(id__in=cluster_ids)
        if not clusters:
            self.log_error(_("查询集群元数据为空，请检查传入的cluster_ids列表是否有问题:{}".format(cluster_ids)))
            return None

        cluster_domains = [c.immute_domain for c in clusters]
        self.log_info(_("-------------------分割线-------------------"))
        self.log_info(_("监听集群有：{}".format(cluster_domains)))
        self.log_info(_("监听的时间区间是：{}-{}".format(datetime2str(flow_tree.created_at), datetime2str(now_time))))
        self.log_info(_("消息收敛开关：{}".format("启用" if enable_converge else "关闭")))

        return {
            "enable_converge": enable_converge,
            "root_id": root_id,
            "flow_tree": flow_tree,
            "ticket_id": ticket_id,
            "clusters": clusters,
            "cluster_domains": cluster_domains,
            "flow_start_time": flow_tree.created_at,
            "now_time": now_time,
        }

    def _call_ai_agent(self, ctx: dict) -> str | None:
        """
        调用AI智能体分析集群告警

        Args:
            ctx: 上下文字典

        Returns:
            str: AI智能体的返回文本，调用失败返回 None
        """
        try:
            # 延迟导入: AgentHandler 依赖的 aidev_bkplugin 仅在 ENABLE_DBM_AI=true 时进入 INSTALLED_APPS
            from backend.dbm_aiagent.agent.handlers import AgentHandler

            db_type = DBType(ctx["flow_tree"].db_type)
            if db_type not in ASK_AI_COMMAND_MAP:
                self.log_warning(_("当前组件类型 {} 暂不支持AI值守，跳过".format(db_type)))
                return None

            # 随机random等待0-30秒， 避免并发调用
            time.sleep(random.randint(0, 30))
            ai_result = AgentHandler.ask_agent_with_command(
                command=ASK_AI_COMMAND_MAP[DBType(ctx["flow_tree"].db_type)].command,
                command_params={
                    "bk_biz_id": ctx["clusters"][0].bk_biz_id,
                    "cluster_domains": ctx["cluster_domains"],
                    "start_time": datetime2str(ctx["flow_start_time"]),
                    "end_time": datetime2str(ctx["now_time"]),
                },
            )
        except Exception as err:
            self.log_error(_("调用智能体分析失败，失败原因：{}".format(err)))
            return None

        self.log_info(_("智能体输出的结果：{}".format(ai_result)))
        return ai_result

    def _handle_no_risk(self, report: FlowWithAITaskGuardianReport):
        """
        处理AI判断无风险的情况，记录无风险状态

        Args:
            report: 收敛记录实例
        """
        try:
            report.record_no_risk()
            self.log_info(_("AI分析结果为无风险，记录无风险检测（连续无风险次数：{}）".format(report.no_risk_streak)))
        except Exception as err:
            self.log_error(_("记录无风险状态失败，失败原因：{}".format(err)))

    def _evaluate_converge(
        self,
        report: FlowWithAITaskGuardianReport,
        enable_converge: bool,
        current_risk_level: str,
        clean_report_text: str,
        db_type: DBType,
    ) -> bool:
        """
        评估是否应该推送（收敛判断核心逻辑）

        包含AI语义比对和退避窗口判断。

        Args:
            report: 收敛记录实例
            enable_converge: 是否启用收敛
            current_risk_level: 当前风险等级
            clean_report_text: 清理标签后的报告文本

        Returns:
            bool: True=应推送，False=应抑制
        """
        # --- AI语义比对（判断是否为同一风险） ---
        is_same_risk = None
        need_compare = (
            enable_converge
            and report.send_count > 0
            and report.last_send_time is not None
            and not report.is_risk_level_upgraded(current_risk_level)
            and report.last_report_content
        )

        if need_compare:
            try:
                self.log_info(_("正在调用智能体比对本次报告与上次报告的风险内容..."))
                is_same_risk = self._compare_reports_with_ai(
                    last_report=report.last_report_content,
                    current_report=clean_report_text,
                    db_type=db_type,
                )
                self.log_info(_("AI比对结果：{}".format("同一风险（收敛）" if is_same_risk else "不同风险（推送）")))
            except Exception as err:
                self.log_error(_("AI语义比对失败（降级为允许推送），失败原因：{}".format(err)))
                is_same_risk = False

        # --- 执行收敛判断 ---
        try:
            should_send, reason = report.should_send(
                current_risk_level=current_risk_level,
                is_same_risk=is_same_risk,
            )
            self.log_info(_("收敛判断：{}，原因：{}".format("允许推送" if should_send else "抑制推送", reason)))
        except Exception as err:
            self.log_error(_("执行收敛判断失败（降级为允许推送），失败原因：{}".format(err)))
            should_send = True

        return should_send

    def _execute_send(
        self,
        report: FlowWithAITaskGuardianReport,
        ticket_id: int,
        current_risk_level: str,
        clean_report_text: str,
    ):
        """
        执行消息推送并更新收敛记录

        Args:
            report: 收敛记录实例
            ticket_id: 单据ID
            current_risk_level: 当前风险等级
            clean_report_text: 清理标签后的报告文本
        """
        # --- 执行消息推送 ---
        try:
            self.log_info(_("正在把AI分析结果推送给提单者..."))
            notify.send_msg_for_ai_task_guardian(ticket_id=ticket_id, ai_result=clean_report_text)
        except Exception as err:
            self.log_error(_("推送AI分析结果给用户失败，失败原因：{}".format(err)))
            return

        # --- 更新收敛记录（存储本次报告作为下次比对的"记忆"） ---
        try:
            report.record_send(risk_level=current_risk_level, report_content=clean_report_text)
            self.log_info(_("推送完成，累计推送次数：{}，报告已存储用于下次比对".format(report.send_count)))
        except Exception as err:
            self.log_error(_("更新收敛记录失败（推送已成功但收敛状态未更新），失败原因：{}".format(err)))

    def sidecar_func(self, data, parent_data) -> bool:
        """
        旁路服务核心函数：监控集群告警并通过AI分析风险（含消息收敛）

        工作流程:
            1. 准备上下文数据（集群信息、流程信息等）
            2. 调用AI智能体分析集群告警
            3. 解析AI结构化结果
            4. 无风险则记录无风险状态
            5. 有风险则执行收敛判断，通过后推送消息

        Args:
            data: Pipeline数据对象
            parent_data: Pipeline父节点数据对象

        Returns:
            bool: 执行结果，True表示成功
        """
        # 阶段1：准备上下文
        ctx = self._prepare_context(data, parent_data)
        if ctx is None:
            return True

        # 阶段2：调用AI智能体
        ai_result = self._call_ai_agent(ctx)
        if ai_result is None:
            return True

        # 阶段3：解析AI返回的结构化结果
        try:
            is_send_info = json.loads(re.search(cpl, ai_result).group("context"))
        except Exception as err:
            self.log_error(_("解析AI返回的结构化结果失败（ai_result标签解析异常），失败原因：{}".format(err)))
            return True

        # 阶段4：获取或创建收敛记录
        try:
            report = self._get_or_create_report(
                root_id=ctx["root_id"], uid=str(ctx["ticket_id"]), enable_converge=ctx["enable_converge"]
            )
        except Exception as err:
            self.log_error(_("获取或创建收敛记录失败，失败原因：{}".format(err)))
            return True

        # 阶段5：无风险处理
        if not (is_send_info and is_send_info.get("is_send_user")):
            self._handle_no_risk(report)
            return True

        # === AI判断有风险，开始收敛判断 ===
        clean_report_text = self._clean_ai_result_tags(ai_result)
        current_risk_level = self._extract_risk_level(is_send_info)
        if current_risk_level:
            self.log_info(_("AI风险等级：{}".format(current_risk_level)))
        else:
            self.log_info(_("AI未返回risk_level，收敛降级为仅基于时间窗口+AI语义比对判断"))

        # 阶段6：收敛评估
        should_send = self._evaluate_converge(
            report=report,
            enable_converge=ctx["enable_converge"],
            current_risk_level=current_risk_level,
            clean_report_text=clean_report_text,
            db_type=DBType(ctx["flow_tree"].db_type),
        )
        if not should_send:
            self.log_info(_("本次推送被收敛策略抑制，跳过推送"))
            return True

        # 阶段7：执行推送并更新记录
        self._execute_send(
            report=report,
            ticket_id=ctx["ticket_id"],
            current_risk_level=current_risk_level,
            clean_report_text=clean_report_text,
        )

        return True


class CheckClusterAlarmForAIComponent(Component):
    """
    集群告警AI检查组件

    Pipeline组件封装类，用于在流程中集成集群告警AI检查服务。
    该组件会作为侧车服务定期运行，监控集群健康状态。

    Attributes:
        name (str): 组件名称，使用模块名
        code (str): 组件唯一标识码
        bound_service (class): 绑定的服务类，指向CheckClusterAlarmForAIService
    """

    name = __name__
    code = "sidecar_check_cluster_alarm_for_ai"
    bound_service = CheckClusterAlarmForAIService
