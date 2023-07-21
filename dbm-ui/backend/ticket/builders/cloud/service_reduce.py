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

from backend.db_proxy.models import DBExtension
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder, BaseServiceOperateSerializer
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudServiceReduceDetailSerializer(BaseServiceOperateSerializer):
    # TODO: 暂不支持nginx缩容
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    old_dns_ids = serializers.ListField(help_text=_("裁撤的dns列表"), child=serializers.IntegerField(), required=False)
    old_drs_ids = serializers.ListField(help_text=_("裁撤的drs列表"), child=serializers.IntegerField(), required=False)
    old_gm_ids = serializers.ListField(help_text=_("裁撤的gm列表"), child=serializers.IntegerField(), required=False)
    old_agent_ids = serializers.ListField(help_text=_("裁撤的agent列表"), child=serializers.IntegerField(), required=False)

    def validate(self, attrs):
        extension_infos = DBExtension.get_extension_info_in_cloud(bk_cloud_id=attrs["bk_cloud_id"])
        # 组件至少保留一台
        for key in ["dns", "drs", "gm", "agent"]:
            self.validate_at_least_one_alive(extension_infos, key, attrs.get(f"old_{key}_ids", []))
        # gm异地部署校验
        if "old_gm_ids" in attrs:
            self.validate_gm_remote_deploy(attrs["old_gm_ids"])
        return attrs


class CloudServiceReduceFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    def format_ticket_data_by_service(self, service_type):
        self.ticket_data["service_type"] = service_type

    def pre_callback(self):
        current_flow = self.ticket.current_flow()
        self.pre_callback_format_ticket_data(current_flow)


class DRSServiceReduceFlowParamBuilder(CloudServiceReduceFlowParamBuilder):
    controller = CloudServiceController.drs_reduce_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(service_type="drs")


class DNSServiceReduceFlowParamBuilder(CloudServiceReduceFlowParamBuilder):
    controller = CloudServiceController.dns_reduce_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(service_type="dns")


class DBHAServiceReduceFlowParamBuilder(CloudServiceReduceFlowParamBuilder):
    controller = CloudServiceController.dbha_reduce_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(service_type="dbha")


@builders.BuilderFactory.register(TicketType.CLOUD_SERVICE_REDUCE)
class CloudServiceApplyFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudServiceReduceDetailSerializer
    editable = False

    def init_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=DNSServiceReduceFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("DNS 服务裁撤"),
            )
            if self.ticket.details.get("old_dns_ids")
            else [],
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=DRSServiceReduceFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("DRS 服务裁撤"),
            )
            if self.ticket.details.get("old_drs_ids")
            else [],
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=DBHAServiceReduceFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("DBHA 服务裁撤"),
            )
            if self.ticket.details.get("old_gm_ids") or self.ticket.details.get("old_agent_ids")
            else [],
        ]
        flows = [flow for flow in flows if flow]
        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("Nginx 服务裁撤"), _("DNS 服务裁撤"), _("DRS 服务裁撤"), _("DBHA 服务裁撤"), _("RedisDts 服务裁撤")]
        return flow_desc
