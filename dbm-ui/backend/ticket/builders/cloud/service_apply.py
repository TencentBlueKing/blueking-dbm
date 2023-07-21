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

from backend.db_proxy.models import DBCloudKit, DBExtension
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import (
    BaseServiceOperateFlowParamBuilder,
    DBHAHostInfoSerializer,
    DNSHostInfoSerializer,
    DRSHostInfoSerializer,
    NginxHostInfoSerializer,
)
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudServiceApplyDetailSerializer(serializers.Serializer):
    class DRSDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署drs服务主机信息"), child=DRSHostInfoSerializer())

    class NginxDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署nginx服务主机信息"), child=NginxHostInfoSerializer())

    class DNSDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署dns服务主机信息"), child=DNSHostInfoSerializer())

    class DBHADetailSerializer(serializers.Serializer):
        agent = serializers.ListField(help_text=_("部署dbha-agent服务主机信息"), child=DBHAHostInfoSerializer())
        gm = serializers.ListField(help_text=_("部署dbha-gm服务主机信息"), child=DBHAHostInfoSerializer())

    class RedisDtsSerializer(serializers.Serializer):
        class RedisDtsHostInfoSerializer(HostInfoSerializer):
            bk_city_name = serializers.CharField(help_text=_("主机城市名"))

        host_infos = serializers.ListField(help_text=_("部署dns服务主机信息"), child=RedisDtsHostInfoSerializer())

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cloud_kit_name = serializers.CharField(help_text=_("套件ID名称"))
    cloud_kit_alias = serializers.CharField(help_text=_("套件别名"), required=False, default="")

    drs = DRSDetailSerializer(help_text=_("drs服务部署信息"))
    nginx = NginxDetailSerializer(help_text=_("nginx服务部署信息"))
    dns = DNSDetailSerializer(help_text=_("dns服务部署信息"))
    dbha = DBHADetailSerializer(help_text=_("dbha服务部署信息"))
    redis_dts = RedisDtsSerializer(help_text=_("redis_dts服务部署信息"), required=False)

    def validate(self, attrs):
        # 如果当前云区域已存在部署组件，则不合法
        if DBExtension.objects.filter(bk_cloud_id=attrs["bk_cloud_id"]).exists():
            raise serializers.ValidationError(_("当前云区域[{}]").format(attrs["bk_cloud_id"]))

        # 校验dbha的gm存在异地部署
        gm_city_codes = [host["bk_city_code"] for host in attrs["dbha"]["gm"]]
        if len(set(gm_city_codes)) == 1:
            raise serializers.ValidationError(_("请保证gm的主机存在异地部署"))


class CloudServiceApplyFlowParamBuilder(builders.FlowParamBuilder):
    def format_ticket_data_by_service(self, ticket_type, service):
        self.ticket_data["ticket_type"] = ticket_type
        self.ticket_data.update(self.ticket_data[service])


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


class RedisDtsServiceApplyFlowParamBuilder(CloudServiceApplyFlowParamBuilder):
    controller = CloudServiceController.redis_dts_server_apply_scene

    def format_ticket_data(self):
        super().format_ticket_data_by_service(ticket_type=TicketType.CLOUD_DBHA_APPLY, service="redis_dts")


@builders.BuilderFactory.register(TicketType.CLOUD_SERVICE_APPLY)
class CloudServiceApplyFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudServiceApplyDetailSerializer
    editable = False

    def init_ticket_flows(self):
        flows = [
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
        ]
        # redis_dts非必选
        if self.ticket.details.get("redis_dts"):
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=RedisDtsServiceApplyFlowParamBuilder(self.ticket).get_params(),
                    flow_alias=_("RedisDts 服务部署"),
                )
            )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    def patch_ticket_detail(self):
        # 创建一个DB套件管理此次部署的组件
        cloud_kit = DBCloudKit.objects.create(
            bk_cloud_id=self.ticket.details["bk_cloud_id"],
            bk_biz_id=self.ticket.details["bk_biz_id"],
            name=self.ticket.details["cloud_kit_name"],
            alias=self.ticket.details["cloud_kit_alias"],
        )
        self.ticket.update_details(cloud_kit=cloud_kit.id)

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("Nginx 服务部署"), _("DNS 服务部署"), _("DRS 服务部署"), _("DBHA 服务部署"), _("RedisDts 服务部署")]
        return flow_desc
