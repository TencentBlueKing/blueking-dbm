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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.ticket import builders
from backend.ticket.builders.common.constants import MySQLChecksumTicketMode
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.builders.mysql.mysql_checksum import FlowRetryType, FlowType, MySQLChecksumFlowBuilder
from backend.ticket.builders.tendbcluster.tendb_checksum import (
    TendbChecksumDetailSerializer,
    TendbChecksumParamBuilder,
    TendbChecksumPauseParamBuilder,
    TendbDataRepairFlowParamBuilder,
)
from backend.ticket.constants import TicketType
from backend.ticket.models import Flow


class TendbChecksumCronDetailSerializer(TendbChecksumDetailSerializer):

    trigger_time = DBTimezoneField(help_text=_("定时触发时间"))
    skip_timer = serializers.BooleanField(help_text=_("是否是定时"))


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_CHECKSUM_CRON)
class TendbChecksumCronFlowBuilder(MySQLChecksumFlowBuilder):
    group = DBType.TenDBCluster.value
    serializer = TendbChecksumCronDetailSerializer
    # 流程构造类
    checksum_flow_builder = TendbChecksumParamBuilder
    pause_flow_builder = TendbChecksumPauseParamBuilder
    data_repair_flow_builder = TendbDataRepairFlowParamBuilder
    editable = False

    def patch_ticket_detail(self):
        BaseMySQLTicketFlowBuilder.patch_ticket_detail(self)

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        return super().describe_ticket_flows(flow_config_map)

    @property
    def need_manual_confirm(self):
        """是否需要人工确认节点。后续默认从单据配置表获取。子类可覆写，覆写以后editable为False"""
        return False

    def custom_ticket_flows(self):
        flows = []
        skip_timer = self.ticket.details["skip_timer"]
        if not skip_timer:
            flows.append(Flow(ticket=self.ticket, flow_type=FlowType.TIMER.value, flow_alias=_("定时执行")))

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.checksum_flow_builder(self.ticket).get_params(),
                flow_alias=_("数据校验执行"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            )
        )

        if self.ticket.details["data_repair"]["is_repair"]:

            if self.ticket.details["data_repair"]["mode"] == MySQLChecksumTicketMode.MANUAL:
                is_auto_describe, retry_type = _("手动"), FlowRetryType.MANUAL_RETRY.value
            else:
                is_auto_describe, retry_type = _("自动"), FlowRetryType.AUTO_RETRY.value

            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    retry_type=retry_type,
                    details=self.data_repair_flow_builder(self.ticket).get_params(),
                    flow_alias=_("数据修复{}执行").format(is_auto_describe),
                ),
            )

        return flows
