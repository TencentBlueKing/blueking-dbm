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
from backend.ticket.builders.cloud.base import (
    BaseServiceOperateFlowParamBuilder,
    DBHAHostInfoSerializer,
    DRSHostInfoSerializer,
)
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudServiceAddDetailSerializer(serializers.Serializer):
    class DRSDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署drs服务主机信息"), child=DRSHostInfoSerializer())

    # TODO: 暂不支持nginx扩容
    # class NginxDetailSerializer(serializers.Serializer):
    #     host_infos = serializers.ListField(help_text=_("部署nginx服务主机信息"), child=NginxHostInfoSerializer())

    class DNSDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署dns服务主机信息"), child=HostInfoSerializer())

    class DBHADetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署dns服务主机信息"), child=DBHAHostInfoSerializer())

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    new_drs = DRSDetailSerializer(help_text=_("drs服务新增部署信息"), default=False)
    new_dns = DNSDetailSerializer(help_text=_("dns服务新增部署信息"), default=False)
    new_gm = DBHADetailSerializer(help_text=_("dbha服务新增部署信息"), default={"host_infos": []})
    new_agent = DBHADetailSerializer(help_text=_("dbha服务新增部署信息"), default={"host_infos": []})

    def validate(self, attrs):
        return attrs


class CloudServiceAddFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    def format_ticket_data_by_service(self, service_type):
        self.ticket_data["service_type"] = service_type

    def pre_callback(self):
        current_flow = self.ticket.current_flow()
        self.pre_callback_format_ticket_data(current_flow)


class DRSServiceAddFlowParamBuilder(CloudServiceAddFlowParamBuilder):
    controller = CloudServiceController.drs_add_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(service_type="drs")


class DNSServiceAddFlowParamBuilder(CloudServiceAddFlowParamBuilder):
    controller = CloudServiceController.dns_add_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(service_type="dns")


class DBHAServiceApplyFlowParamBuilder(CloudServiceAddFlowParamBuilder):
    controller = CloudServiceController.dbha_add_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(service_type="dbha")


@builders.BuilderFactory.register(TicketType.CLOUD_SERVICE_ADD)
class CloudServiceApplyFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudServiceAddDetailSerializer
    editable = False

    def init_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=DNSServiceAddFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("DNS 服务新增"),
            )
            if self.ticket.details.get("new_dns")
            else [],
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=DRSServiceAddFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("DRS 服务新增"),
            )
            if self.ticket.details.get("new_dns")
            else [],
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=DBHAServiceApplyFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("DBHA 服务新增"),
            )
            if self.ticket.details["new_gm"]["host_infos"] or self.ticket.details["new_agent"]["host_infos"]
            else [],
        ]
        flows = [flow for flow in flows if flow]
        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("Nginx 服务新增"), _("DNS 服务新增"), _("DRS 服务新增"), _("DBHA 服务新增"), _("RedisDts 服务新增")]
        return flow_desc
