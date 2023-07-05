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
from collections import defaultdict
from typing import Any, Dict

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType
from backend.ticket.constants import (
    EXCLUSIVE_TICKET_EXCEL_PATH,
    FlowRetryType,
    FlowType,
    TicketFlowStatus,
    TicketStatus,
    TicketType,
)
from backend.utils.excel import ExcelHandler
from backend.utils.time import calculate_cost_time

logger = logging.getLogger("root")


class Flow(models.Model):
    """
    单据流程
    """

    create_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    update_at = models.DateTimeField(_("更新时间"), auto_now=True)
    ticket = models.ForeignKey("Ticket", help_text=_("关联工单"), related_name="flows", on_delete=models.CASCADE)
    flow_type = models.CharField(help_text=_("流程类型"), max_length=LEN_SHORT, choices=FlowType.get_choices())
    flow_alias = models.CharField(help_text=_("流程别名"), max_length=LEN_LONG, null=True, blank=True)
    # 若 flow_type 为 itsm，则 flow_obj_id 为 ITSM 单据号；若为 job，则对应 job_id；内置流程为 root_id；可扩展
    flow_obj_id = models.CharField(_("单据流程对象ID"), max_length=LEN_NORMAL, blank=True)
    details = models.JSONField(_("单据流程详情"), default=dict)
    status = models.CharField(
        _("单据流程状态"),
        choices=TicketFlowStatus.get_choices(),
        max_length=LEN_SHORT,
        default=TicketFlowStatus.PENDING,
    )
    err_msg = models.TextField(_("错误信息"), null=True, blank=True)
    err_code = models.FloatField(_("错误代码"), null=True, blank=True)
    retry_type = models.CharField(
        _("重试类型(专用于inner_flow)"), max_length=LEN_SHORT, choices=FlowRetryType.get_choices(), blank=True, null=True
    )

    class Meta:
        verbose_name = _("单据流程")
        verbose_name_plural = _("单据流程")

    def update_details(self, **kwargs):
        self.details.update(kwargs)
        self.save(update_fields=["details", "update_at"])
        return kwargs

    def update_status(self, status: TicketFlowStatus):
        if self.status == status:
            return

        self.status = status
        self.save(update_fields=["status", "update_at"])
        return status


class Ticket(AuditedModel):
    """
    单据
    """

    bk_biz_id = models.IntegerField(_("业务ID"))
    ticket_type = models.CharField(
        _("单据类型"),
        choices=TicketType.get_choices(),
        max_length=LEN_NORMAL,
        default=TicketType.MYSQL_SINGLE_APPLY,
    )
    group = models.CharField(_("单据分组类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL)
    status = models.CharField(
        _("单据状态"),
        choices=TicketStatus.get_choices(),
        max_length=LEN_SHORT,
        default=TicketStatus.PENDING,
    )
    remark = models.CharField(_("备注"), max_length=LEN_MIDDLE)
    details = models.JSONField(_("单据差异化详情"), default=dict)
    is_reviewed = models.BooleanField(_("单据是否审阅过"), default=False)

    class Meta:
        verbose_name = _("单据")
        verbose_name_plural = _("单据")
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["creator"]),
            models.Index(fields=["bk_biz_id"]),
            models.Index(fields=["group"]),
            models.Index(fields=["status"]),
        ]

    def set_failed(self):
        self.status = TicketStatus.FAILED
        self.save()

    def get_cost_time(self):
        # 计算耗时
        if self.status in [TicketStatus.PENDING, TicketStatus.RUNNING]:
            return calculate_cost_time(timezone.now(), self.create_at)
        return calculate_cost_time(self.update_at, self.create_at)

    def update_details(self, **kwargs):
        self.details.update(kwargs)
        self.save(update_fields=["details", "update_at"])

    def update_flow_details(self, **kwargs):
        self.current_flow().update_details(**kwargs)

    def current_flow(self) -> Flow:
        """
        当前的流程
         1. 取 TicketFlow 中最后一个 flow_obj_id 非空的流程
         2. 若 TicketFlow 中都流程都为空，则代表整个单据未开始，取第一个流程
        """
        if Flow.objects.filter(ticket=self).exclude(status=TicketFlowStatus.PENDING).exists():
            return Flow.objects.filter(ticket=self).exclude(status=TicketFlowStatus.PENDING).last()
        # 初始化时，当前节点和下一个节点为同一个
        return self.next_flow()

    def next_flow(self) -> Flow:
        """
        下一个流程，即 TicketFlow 中第一个为PENDING的流程
        """
        next_flows = Flow.objects.filter(ticket=self, status=TicketFlowStatus.PENDING)

        # 支持跳过人工审批和确认环节
        if env.ITSM_FLOW_SKIP:
            next_flows = next_flows.exclude(flow_type__in=[FlowType.BK_ITSM, FlowType.PAUSE])

        return next_flows.first()

    @classmethod
    def create_ticket(
        cls,
        ticket_type: TicketType,
        creator: str,
        bk_biz_id: int,
        remark: str,
        details: Dict[str, Any],
        auto_execute: bool = True,
    ) -> None:
        """
        自动创建单据
        :param ticket_type: 单据类型
        :param creator: 创建者
        :param bk_biz_id: 业务ID
        :param remark: 备注
        :param details: 单据参数details
        :param auto_execute: 是否自动初始化执行单据
        """

        from backend.ticket.builders import BuilderFactory

        with transaction.atomic():
            ticket = Ticket.objects.create(
                group=BuilderFactory.get_builder_cls(ticket_type).group,
                creator=creator,
                updater=creator,
                bk_biz_id=bk_biz_id,
                ticket_type=ticket_type,
                remark=remark,
                details=details,
            )
            logger.info(_("正在自动创建单据，单据详情: {}").format(ticket.__dict__))
            builder = BuilderFactory.create_builder(ticket)
            builder.patch_ticket_detail()
            builder.init_ticket_flows()

        if auto_execute:
            # 开始单据流程
            from backend.ticket.flow_manager.manager import TicketFlowManager

            logger.info(_("单据{}正在初始化流程").format(ticket.id))
            TicketFlowManager(ticket=ticket).run_next_flow()


class ClusterOperateRecordManager(models.Manager):
    def filter_actives(self, cluster_id, **kwargs):
        """获得集群正在运行的单据"""
        return self.filter(cluster_id=cluster_id, flow__status=TicketFlowStatus.RUNNING, **kwargs)

    def get_cluster_operations(self, cluster_id, **kwargs):
        """集群上的操作列表"""
        return [r.summary for r in self.filter_actives(cluster_id, **kwargs)]

    def has_exclusive_operations(self, ticket_type, cluster_id, **kwargs):
        """判断当前单据类型与集群正在进行中的单据是否互斥"""
        active_tickets = self.filter_actives(cluster_id, **kwargs)
        exclusive_infos = []
        for active_ticket in active_tickets:
            try:
                if self.exclusive_ticket_map[ticket_type][active_ticket.ticket.ticket_type]:
                    exclusive_infos.append(
                        {"exclusive_ticket": active_ticket.ticket, "root_id": active_ticket.flow.flow_obj_id}
                    )
            except KeyError:
                pass

        return exclusive_infos

    @property
    def exclusive_ticket_map(self):
        if hasattr(self, "_exclusive_ticket_map"):
            return self._exclusive_ticket_map

        _exclusive_matrix = ExcelHandler.paser_matrix(EXCLUSIVE_TICKET_EXCEL_PATH)
        _exclusive_ticket_map = defaultdict(dict)
        for row_key, inner_dict in _exclusive_matrix.items():
            for col_key, value in inner_dict.items():
                row_key, col_key = TicketType.get_choice_value(row_key), TicketType.get_choice_value(col_key)
                _exclusive_ticket_map[row_key][col_key] = value == "N"

        setattr(self, "_exclusive_ticket_map", _exclusive_ticket_map)
        return self._exclusive_ticket_map


class ClusterOperateRecord(AuditedModel):
    """
    集群操作记录
    """

    cluster_id = models.IntegerField(_("集群ID"))
    flow = models.ForeignKey("Flow", help_text=_("关联流程任务"), on_delete=models.CASCADE)
    ticket = models.ForeignKey("Ticket", help_text=_("关联工单"), on_delete=models.CASCADE)

    objects = ClusterOperateRecordManager()

    class Meta:
        # cluster_id, flow和ticket组成唯一性校验
        unique_together = (("cluster_id", "flow", "ticket"),)

    @property
    def summary(self):
        return {
            "operator": self.creator,
            "cluster_id": self.cluster_id,
            "flow_id": self.flow.id,
            "ticket_id": self.ticket.id,
            "ticket_type": self.ticket.ticket_type,
            "title": self.ticket.get_ticket_type_display(),
            "status": self.ticket.status,
        }


class InstanceOperateRecordManager(models.Manager):
    LOCKED_TICKET_TYPES = {
        TicketType.ES_REBOOT,
        TicketType.KAFKA_REBOOT,
        TicketType.HDFS_REBOOT,
        TicketType.INFLUXDB_REBOOT,
        TicketType.PULSAR_REBOOT,
    }

    def filter_actives(self, instance_id, **kwargs):
        return self.filter(
            instance_id=instance_id,
            ticket__status__in=[TicketStatus.RUNNING, TicketStatus.PENDING],
            ticket__ticket_type__in=self.LOCKED_TICKET_TYPES,
            **kwargs,
        )

    def get_locking_operations(self, instance_id, **kwargs):
        """实例上的锁定操列表"""
        return [r.summary for r in self.filter_actives(instance_id, **kwargs)]

    def has_locked_operations(self, instance_id, **kwargs):
        """是否有锁定实例的操作在执行"""
        return self.filter_actives(instance_id, **kwargs).exists()


class InstanceOperateRecord(AuditedModel):
    """
    实例操作记录
    TODO: 是否考虑定期清理记录
    """

    instance_id = models.IntegerField(_("实例ID"))

    flow = models.ForeignKey("Flow", help_text=_("关联流程任务"), on_delete=models.CASCADE)
    ticket = models.ForeignKey("Ticket", help_text=_("关联工单"), on_delete=models.CASCADE)

    objects = InstanceOperateRecordManager()

    @property
    def summary(self):
        return {
            "operator": self.creator,
            "instance_id": self.instance_id,
            "flow_id": self.flow.id,
            "ticket_id": self.ticket.id,
            "ticket_type": self.ticket.ticket_type,
            "title": self.ticket.get_ticket_type_display(),
            "status": self.ticket.status,
        }
