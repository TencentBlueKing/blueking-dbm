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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudServiceApplyDetailSerializer(serializers.Serializer):
    class DRSDetailSerialzier(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署drs服务主机信息"), child=serializers.DictField())

    class NginxDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署nginx服务主机信息"), child=serializers.DictField())

    class DNSDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署dns服务主机信息"), child=serializers.DictField())

    class DBHADetailSerializer(serializers.Serializer):
        agent = serializers.ListField(help_text=_("部署dbha-agent服务主机信息"), child=serializers.DictField())
        gm = serializers.ListField(help_text=_("部署dbha-gm服务主机信息"), child=serializers.DictField())

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    drs = DRSDetailSerialzier(help_text=_("drs服务部署信息"))
    nginx = NginxDetailSerializer(help_text=_("nginx服务部署信息"))
    dns = DNSDetailSerializer(help_text=_("dns服务部署信息"))
    dbha = DBHADetailSerializer(help_text=_("dbha服务部署信息"))


class CloudServiceApplyItsmParamBuilder(builders.ItsmParamBuilder):
    def format(self):
        self.details[_("云区域ID")] = self.details.pop("bk_cloud_id")
        self.details[_("drs服务部署信息")] = self.details.pop("drs")
        self.details[_("nginx服务部署信息")] = self.details.pop("nginx")
        self.details[_("dns服务部署信息")] = self.details.pop("dns")
        self.details[_("dbha服务部署信息")] = self.details.pop("dbha")


class CloudServiceApplyFlowParamBuilder(builders.FlowParamBuilder):
    def _remove_redundant_params(self):
        self.ticket_data.pop("drs")
        self.ticket_data.pop("nginx")
        self.ticket_data.pop("dns")
        self.ticket_data.pop("dbha")

    def format_ticket_data_by_service(self, ticket_type, service):
        self.ticket_data["ticket_type"] = ticket_type
        self.ticket_data.update(self.ticket_data[service])
        # 保留其他组件的部署信息
        # self._remove_redundant_params()


class NginxServiceApplyFlowParamBuilder(CloudServiceApplyFlowParamBuilder):
    controller = CloudServiceController.nginx_apply_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(ticket_type=TicketType.CLOUD_NGINX_APPLY, service="nginx")


class DRSServiceApplyFlowParamBuilder(CloudServiceApplyFlowParamBuilder):
    controller = CloudServiceController.drs_apply_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(ticket_type=TicketType.CLOUD_DRS_APPLY, service="drs")


class DNSServiceApplyFlowParamBuilder(CloudServiceApplyFlowParamBuilder):
    controller = CloudServiceController.dns_apply_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(ticket_type=TicketType.CLOUD_DNS_APPLY, service="dns")


class DBHAServiceApplyFlowParamBuilder(CloudServiceApplyFlowParamBuilder):
    controller = CloudServiceController.dbha_apply_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(ticket_type=TicketType.CLOUD_DBHA_APPLY, service="dbha")
        BaseServiceOperateFlowParamBuilder.padding_dbha_type(self.ticket_data)


@builders.BuilderFactory.register(TicketType.CLOUD_SERVICE_APPLY)
class CloudServiceApplyFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudServiceApplyDetailSerializer

    def init_ticket_flows(self):
        Flow.objects.bulk_create(
            [
                # Flow(
                #     ticket=self.ticket,
                #     flow_type=FlowType.BK_ITSM.value,
                #     details=CloudServiceApplyItsmParamBuilder(self.ticket).get_params(),
                # ),
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=NginxServiceApplyFlowParamBuilder(self.ticket).get_params(),
                    flow_alias=_("Nginx 服务部署"),
                ),
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=DNSServiceApplyFlowParamBuilder(self.ticket).get_params(),
                    flow_alias=_("DNS 服务部署"),
                ),
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=DRSServiceApplyFlowParamBuilder(self.ticket).get_params(),
                    flow_alias=_("DRS 服务部署"),
                ),
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=DBHAServiceApplyFlowParamBuilder(self.ticket).get_params(),
                    flow_alias=_("DBHA 服务部署"),
                ),
                Flow(ticket=self.ticket, flow_type=FlowType.DELIVERY.value),
            ]
        )
        return list(Flow.objects.filter(ticket=self.ticket))
