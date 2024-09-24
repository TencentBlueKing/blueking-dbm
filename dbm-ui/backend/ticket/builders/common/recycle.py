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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpDest
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.ticket import builders
from backend.ticket.builders import RecycleParamBuilder, ReImportResourceParamBuilder, TicketFlowBuilder
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class RecycleHostDetailSerializer(serializers.Serializer):
    recycle_hosts = serializers.JSONField(help_text=_("机器回收信息"))
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收流向"))


class RecycleHostResourceParamBuilder(ReImportResourceParamBuilder):
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


@builders.BuilderFactory.register(TicketType.RECYCLE_HOST)
class RecycleHostFlowBuilder(TicketFlowBuilder):
    serializer = RecycleHostDetailSerializer
    import_resource_flow_builder = RecycleHostResourceParamBuilder
    recycle_flow_builder = RecycleHostParamBuilder
    # 此单据不属于任何db，暂定为common
    group = "common"

    def init_ticket_flows(self):
        # 主机清理
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.HOST_RECYCLE.value,
                details=self.recycle_flow_builder(self.ticket).get_params(),
            ),
        ]
        # 导入资源池
        if self.ticket.details["ip_recycle"]["ip_dest"] == IpDest.Resource:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.HOST_IMPORT_RESOURCE.value,
                    details=self.import_resource_flow_builder(self.ticket).get_params(),
                ),
            )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    def patch_ticket_detail(self):
        recycle_hosts = self.ticket.details["recycle_hosts"]
        self.ticket.update_details(recycle_hosts=ResourceHandler.standardized_resource_host(recycle_hosts))
