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
from backend.db_services.dbbase.constants import IpDest
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.ticket import builders
from backend.ticket.builders import (
    ImportPoolParamBuilder,
    ImportResourceParamBuilder,
    RecycleParamBuilder,
    TicketFlowBuilder,
)
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


class RecycleHostDetailSerializer(serializers.Serializer):
    recycle_hosts = serializers.JSONField(help_text=_("机器回收信息"))
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收流向"))


class RecycleHostResourceParamBuilder(ImportResourceParamBuilder):
    def format_ticket_data(self):
        # 导入资源的类型设置为预设的group
        group = self.ticket_data["group"]
        super().format_ticket_data()
        self.ticket_data["resource_type"] = group


class RecycleHostParamBuilder(RecycleParamBuilder):
    def format_ticket_data(self):
        group = self.ticket_data["group"]
        super().format_ticket_data()
        self.ticket_data["db_type"] = group


class RecycleHostFlowBuilder(TicketFlowBuilder):
    serializer = RecycleHostDetailSerializer
    import_resource_flow_builder = RecycleHostResourceParamBuilder
    import_pool_builder = ImportPoolParamBuilder
    recycle_flow_builder = RecycleHostParamBuilder
    # 此单据不属于任何db，暂定为common
    group = "common"

    def init_ticket_flows(self):
        flows = []

        # 定时执行
        if env.HOST_RECYCLE_RETENTION_DAYS:
            flows.append(
                Flow(ticket=self.ticket, flow_type=FlowType.TIMER.value, flow_alias=_("定时执行")),
            )

        # 数据清理
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.HOST_RECYCLE.value,
                details=self.recycle_flow_builder(self.ticket).get_params(),
                flow_alias=_("主机数据清理"),
            ),
        )

        ip_dest = self.ticket.details["ip_recycle"]["ip_dest"]
        # 导入资源池
        if ip_dest == IpDest.Resource:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.HOST_RECYCLE.value,
                    details=self.import_resource_flow_builder(self.ticket).get_params(),
                    flow_alias=_("主机退回资源池"),
                ),
            )

        # 导入故障池、待回收池
        if ip_dest in [IpDest.Fault, IpDest.Recycle]:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.HOST_RECYCLE.value,
                    details=self.import_pool_builder(self.ticket).get_params(),
                    flow_alias=_("主机转入{}".format(IpDest.get_choice_label(ip_dest))),
                ),
            )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    def patch_ticket_detail(self):
        trigger_time = datetime2str(datetime.now(timezone.utc) + timedelta(days=env.HOST_RECYCLE_RETENTION_DAYS))
        recycle_hosts = ResourceHandler.standardized_resource_host(self.ticket.details["recycle_hosts"])
        self.ticket.update_details(recycle_hosts=recycle_hosts, trigger_time=trigger_time)


@builders.BuilderFactory.register(TicketType.RECYCLE_APPLY_HOST)
class RecycleApplyHostFlowBuilder(RecycleHostFlowBuilder):
    pass


@builders.BuilderFactory.register(TicketType.RECYCLE_OLD_HOST)
class RecycleOldHostFlowBuilder(RecycleHostFlowBuilder):
    pass
