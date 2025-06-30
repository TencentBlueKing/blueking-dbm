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
from datetime import datetime, timedelta, timezone

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.configuration.models import BizSettings
from backend.flow.engine.controller.base import BaseController
from backend.ticket import builders
from backend.ticket.builders import FlowParamBuilder, RecycleCleanMachineParamBuilder, TicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


class RecycleHostDetailSerializer(serializers.Serializer):
    recycle_hosts = serializers.JSONField(help_text=_("下架机器的回收信息"), default=[])
    group = serializers.ChoiceField(help_text=_("所属组件"), choices=DBType.get_choices())
    parent_ticket = serializers.IntegerField(help_text=_("发起单据号"))


class MachineIdleCheckParamBuilder(FlowParamBuilder):
    controller = BaseController.machine_idle_check_flow

    def format_ticket_data(self):
        hosts = self.ticket_data["recycle_hosts"]
        self.ticket_data.update(
            {
                "bk_biz_id": self.ticket.bk_biz_id,
                "ticket_id": self.ticket.id,
                "sa_check_ips": [recycle["ip"] for recycle in hosts],
                "operator": self.ticket.creator,
                "db_type": self.ticket_data["group"],
            }
        )


class RecycleHostParamBuilder(FlowParamBuilder):
    controller = BaseController.machine_recycle_flow

    def format_ticket_data(self):
        self.ticket_data.update(db_type=self.ticket_data["group"], operator=self.ticket.creator)


class RecycleHostFlowBuilder(TicketFlowBuilder):
    serializer = RecycleHostDetailSerializer
    machine_clean_flow_builder = RecycleCleanMachineParamBuilder
    machine_idle_check_flow_builder = MachineIdleCheckParamBuilder
    recycle_flow_builder = RecycleHostParamBuilder
    # 此单据不属于任何db，暂定为common
    group = "common"
    editable = False

    def check_independent_recycle(self):
        hosting_biz = BizSettings.get_exact_hosting_biz(self.ticket.bk_biz_id, self.ticket.details["group"])
        return self.ticket.ticket_type == TicketType.RECYCLE_OLD_HOST and hosting_biz != env.DBA_APP_BK_BIZ_ID

    def init_ticket_flows(self):
        flows = []

        # 对于独立管控的回收单，跳过空闲检查和数据清理
        if not self.check_independent_recycle():
            # 定时执行
            if env.HOST_RECYCLE_RETENTION_DAYS:
                flows.append(
                    Flow(ticket=self.ticket, flow_type=FlowType.TIMER.value, flow_alias=_("定时执行")),
                )

            # 主机空闲检查
            if env.SA_CHECK_TEMPLATE_ID:
                flows.append(
                    Flow(
                        ticket=self.ticket,
                        flow_type=FlowType.HOST_RECYCLE.value,
                        details=self.machine_idle_check_flow_builder(self.ticket).get_params(),
                        flow_alias=_("主机空闲检查"),
                    ),
                )

            # 数据清理
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.HOST_RECYCLE.value,
                    details=self.machine_clean_flow_builder(self.ticket).get_params(),
                    flow_alias=_("主机数据清理"),
                ),
            )

        # 主机分池处理
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.HOST_RECYCLE.value,
                details=self.recycle_flow_builder(self.ticket).get_params(),
                flow_alias=_("主机分池处理"),
            ),
        )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    def patch_ticket_detail(self):
        trigger_time = datetime2str(datetime.now(timezone.utc) + timedelta(days=env.HOST_RECYCLE_RETENTION_DAYS))
        self.ticket.update_details(trigger_time=trigger_time)


@builders.BuilderFactory.register(TicketType.RECYCLE_APPLY_HOST)
class RecycleApplyHostFlowBuilder(RecycleHostFlowBuilder):
    pass


@builders.BuilderFactory.register(TicketType.RECYCLE_OLD_HOST)
class RecycleOldHostFlowBuilder(RecycleHostFlowBuilder):
    pass
