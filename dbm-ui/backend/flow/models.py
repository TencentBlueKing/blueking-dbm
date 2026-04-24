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
from typing import Union

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_NORMAL
from backend.configuration.constants import DBType
from backend.flow.consts import FlowNodeOperateType, StateType
from backend.ticket.constants import TicketType


class FlowTree(models.Model):
    bk_biz_id = models.IntegerField(_("业务ID"))
    uid = models.CharField(_("单据ID"), max_length=127, db_index=True, blank=True, null=True)
    db_type = models.CharField(_("组件类型"), choices=DBType.get_choices(), max_length=64, default="")
    ticket_type = models.CharField(_("单据类型"), choices=TicketType.get_choices(), max_length=64)
    root_id = models.CharField(_("流程ID"), max_length=33, primary_key=True)
    tree = models.JSONField(_("流程树"), null=True, blank=True)
    status = models.CharField(
        _("流程状态"), default=StateType.CREATED.value, choices=StateType.get_choices(), max_length=20
    )
    created_by = models.CharField(_("流程创建人"), max_length=20, null=True)
    created_at = models.DateTimeField(_("启动时间"), auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(_("流程结束时间"), auto_now=True, blank=True)
    is_expired = models.BooleanField(_("是否已经过期"), default=False, help_text=_("运行时被定期清理即为过期"))

    class Meta:
        db_table = "flow_tree"
        ordering = ("-created_at",)
        index_together = [("bk_biz_id", "db_type")]


class FlowNode(models.Model):
    uid = models.CharField(_("单据ID"), max_length=127, blank=True, null=True)
    root_id = models.CharField(_("流程ID"), max_length=33)
    node_id = models.CharField(_("节点ID"), max_length=33)
    version_id = models.CharField(_("当前版本ID"), max_length=33, blank=True)
    status = models.CharField(
        _("节点状态"), default=StateType.CREATED.value, choices=StateType.get_choices(), max_length=20
    )
    hosts = models.JSONField(_("节点运行时IP"), blank=True, null=True, default=list)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True, blank=True)
    started_at = models.DateTimeField(_("开始执行时间"), blank=True, null=True)
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True, blank=True)
    is_expired = models.BooleanField(_("是否已经过期"), default=False, help_text=_("运行时被定期清理即为过期"))

    class Meta:
        unique_together = ["root_id", "node_id", "version_id"]
        db_table = "flow_node"


class FlowNodeOperateRecord(models.Model):
    root_id = models.CharField(_("流程ID"), max_length=33)
    node_id = models.CharField(_("节点ID"), max_length=33)
    version_id = models.CharField(_("版本ID"), max_length=33, blank=True)

    operator = models.CharField(_("操作人"), max_length=128)
    operate_type = models.CharField(_("操作类型"), choices=FlowNodeOperateType.get_choices(), max_length=64)
    operate_date = models.DateTimeField(_("操作时间"), auto_now_add=True)
    remark = models.CharField(_("备注"), max_length=128, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["root_id"]),
            models.Index(fields=["node_id"]),
        ]
        db_table = "flow_node_operate_record"

    @classmethod
    def insert_record(cls, flow: Union[str, FlowNode], operator: str, operate_type: str, remark: str = "", **options):
        # 如果这里传入的flow只是node_id，请务必在options至少传入root_id，否则查询会很慢
        if isinstance(flow, str):
            node_filter = {"node_id": flow}
            # 加速查询
            if options.get("root_id"):
                node_filter["root_id"] = options["root_id"]
            if options.get("version_id"):
                node_filter["version_id"] = options["version_id"]
            flow = FlowNode.objects.get(**node_filter)

        cls.objects.create(
            root_id=flow.root_id,
            node_id=flow.node_id,
            version_id=flow.version_id,
            operator=operator,
            operate_type=operate_type,
            remark=remark,
        )
        return flow

    @classmethod
    def insert_root_record(cls, root_id, operator: str, operate_type: str):
        # 仅插入流程的记录，此时node_id和version_id为空
        cls.objects.create(root_id=root_id, node_id="", version_id="", operator=operator, operate_type=operate_type)


class FlowWithAITaskGuardianReport(models.Model):
    uid = models.CharField(_("单据ID"), max_length=127, blank=True, default="")
    root_id = models.CharField(_("流程ID"), max_length=33)

    # ---- 收敛相关字段 ----
    enable_converge = models.BooleanField(_("是否启用消息收敛"), default=True, help_text=_("默认启用，设为False则每次有风险都推送"))
    send_count = models.IntegerField(_("已推送次数"), default=0)
    last_send_time = models.DateTimeField(_("最后一次推送时间"), null=True, blank=True)
    last_risk_level = models.CharField(_("最后一次推送的风险等级"), max_length=20, default="", blank=True)
    last_report_content = models.TextField(
        _("最后一次推送的风险报告内容"), default="", blank=True, help_text=_("存储上一次推送的完整风险报告，用于与本次报告进行AI语义比对，判断是否为同一风险")
    )
    no_risk_streak = models.IntegerField(_("连续无风险检测次数"), default=0, help_text=_("连续N次检测无风险后重置退避计数器"))

    # ---- 收敛策略常量 ----
    BASE_INTERVAL = 5 * 60  # 基础退避间隔: 5分钟
    MAX_INTERVAL = 2 * 60 * 60  # 最大退避间隔: 2小时
    NO_RISK_RESET_THRESHOLD = 3  # 连续无风险重置阈值

    # 风险等级排序（数值越大越严重）
    RISK_LEVEL_ORDER = {
        "": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    class Meta:
        db_table = "flow_with_ai_task_guardian_report"
        unique_together = ["uid", "root_id"]

    def _get_current_converge_window(self) -> int:
        """
        计算当前的收敛窗口时长（秒）
        公式: min(BASE_INTERVAL * 2^(send_count-1), MAX_INTERVAL)
        """
        if self.send_count <= 0:
            return 0
        exponent = self.send_count - 1
        interval = self.BASE_INTERVAL * (2**exponent)
        return min(interval, self.MAX_INTERVAL)

    def is_risk_level_upgraded(self, current_risk_level: str) -> bool:
        """
        判断当前风险等级是否比上次推送时的等级更高
        如果传入空字符串（智能体未返回risk_level），视为等级未变化
        """
        if not current_risk_level:
            return False
        current_order = self.RISK_LEVEL_ORDER.get(current_risk_level, 0)
        last_order = self.RISK_LEVEL_ORDER.get(self.last_risk_level, 0)
        return current_order > last_order

    def _is_in_converge_window(self) -> tuple:
        """
        判断当前是否在收敛窗口内

        Returns:
            tuple: (is_in_window: bool, remaining_seconds: int)
        """
        from django.utils import timezone

        if self.last_send_time is None:
            return False, 0

        converge_window = self._get_current_converge_window()
        elapsed = (timezone.now() - self.last_send_time).total_seconds()
        if elapsed < 0:
            # 时钟回拨，视为窗口已过，允许推送
            return False, 0

        if elapsed >= converge_window:
            return False, 0
        return True, int(converge_window - elapsed)

    def should_send(self, current_risk_level: str = "", is_same_risk: bool = None) -> tuple:
        """
        核心收敛判断：是否应该推送消息

        判断优先级：
            1. 收敛未启用 → 直接推送
            2. 首次推送 → 立即推送
            3. 风险等级升级 → 打破沉默窗口，立即推送
            4. AI判定非同一风险 → 打破沉默窗口，立即推送（新风险点）
            5. 超过收敛时间窗口 → 允许推送
            6. 以上都不满足 → 抑制推送

        Args:
            current_risk_level: 当前AI分析的风险等级，可为空
            is_same_risk: AI比对结果，True=同一风险/False=不同风险/None=未比对（首次或比对失败）

        Returns:
            tuple: (should_send: bool, reason: str)
        """
        # 规则0：如果未启用收敛，直接放行
        if not self.enable_converge:
            return True, _("收敛未启用，直接推送")

        # 规则1：从未推送过，立即推送
        if self.send_count == 0 or self.last_send_time is None:
            return True, _("首次发现风险，立即推送")

        # 规则2：风险等级升级，打破沉默窗口
        if self.is_risk_level_upgraded(current_risk_level):
            return True, _("风险等级升级: {} -> {}，立即推送").format(self.last_risk_level, current_risk_level)

        # 规则3：AI判定为不同风险（新风险点），打破沉默窗口
        if is_same_risk is False:
            return True, _("AI判定为不同风险（新风险点），立即推送")

        # 规则4：判断是否超过收敛窗口
        is_in_window, remaining = self._is_in_converge_window()
        if not is_in_window:
            converge_window = self._get_current_converge_window()
            return True, _("收敛窗口({}s)已过，允许推送").format(converge_window)

        # 在收敛窗口内，抑制推送
        return False, _("在收敛窗口内，距下次允许推送还有{} s").format(remaining)

    def record_send(self, risk_level: str = "", report_content: str = ""):
        """
        记录一次成功推送，更新退避状态和报告内容

        Args:
            risk_level: 本次风险等级
            report_content: 本次风险报告的完整文本（用于下次AI比对）
        """
        from django.utils import timezone

        self.send_count += 1
        self.last_send_time = timezone.now()
        if risk_level:
            self.last_risk_level = risk_level
        if report_content:
            self.last_report_content = report_content
        self.no_risk_streak = 0
        self.save(
            update_fields=["send_count", "last_send_time", "last_risk_level", "last_report_content", "no_risk_streak"]
        )

    def record_no_risk(self):
        """
        记录一次无风险检测结果
        连续N次无风险后重置退避计数器
        """
        self.no_risk_streak += 1
        if self.no_risk_streak >= self.NO_RISK_RESET_THRESHOLD:
            self.send_count = 0
            self.last_send_time = None
            self.last_risk_level = ""
            self.last_report_content = ""
            self.no_risk_streak = 0
            self.save(
                update_fields=[
                    "send_count",
                    "last_send_time",
                    "last_risk_level",
                    "last_report_content",
                    "no_risk_streak",
                ]
            )
        else:
            self.save(update_fields=["no_risk_streak"])


class FlowBkJobInstance(models.Model):
    """
    记录一次蓝鲸作业 fast_execute_script 的 job_instance_id 与流程/单据的对应关系
    ticket_id 可为空：直接发起任务、不经过单据时与 FlowTree.uid 一样无单据 ID
    """

    ticket_id = models.PositiveIntegerField(_("单据ID"), null=True, blank=True, db_index=True)
    root_id = models.CharField(_("流程任务ID"), max_length=33, db_index=True)
    job_instance_id = models.BigIntegerField(_("蓝鲸作业实例ID"), db_index=True)
    step_instance_id = models.BigIntegerField(
        _("蓝鲸步骤实例ID"), null=True, blank=True, db_index=True, help_text=_("可选，尽力从任务返回或 job 状态接口解析")
    )
    node_id = models.CharField(_("节点ID"), max_length=33)
    version_id = models.CharField(_("版本ID"), max_length=33, blank=True, default="")
    node_name = models.CharField(_("节点名称"), max_length=LEN_NORMAL, blank=True, default="")
    component_code = models.CharField(_("组件代码"), max_length=LEN_NORMAL, blank=True, default="")
    cluster_id = models.PositiveIntegerField(
        _("集群ID"), null=True, blank=True, db_index=True, help_text=_("可选，仅当上下文中能确定集群主键时写入")
    )
    exec_ips = models.JSONField(
        _("执行目标IP"),
        null=True,
        blank=True,
        help_text=_("可选，与节点实际下发的 exec_ip 一致，可能为 IP 字符串或含 ip/bk_cloud_id 的字典列表"),
    )
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True, blank=True)

    class Meta:
        db_table = "flow_bk_job_instance"
        indexes = [
            models.Index(
                fields=["root_id", "node_id", "version_id"],
                name="flow_bk_jobinst_rnv_idx",
            ),
        ]
