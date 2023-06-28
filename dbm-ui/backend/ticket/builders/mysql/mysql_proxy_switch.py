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

from backend.db_meta.enums import AccessLayer, ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    HostInfoSerializer,
    InstanceInfoSerializer,
)
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MysqlProxySwitchDetailSerializer(MySQLBaseOperateDetailSerializer):
    class SwitchInfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        origin_proxy = InstanceInfoSerializer(help_text=_("旧Proxy实例信息"))
        target_proxy = HostInfoSerializer(help_text=_("新Proxy机器信息"), required=False)
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    force = serializers.BooleanField(help_text=_("是否强制替换"), required=False, default=False)
    infos = serializers.ListField(help_text=_("替换信息"), child=SwitchInfoSerializer())

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super(MysqlProxySwitchDetailSerializer, self).validate_cluster_can_access(attrs)
        super(MysqlProxySwitchDetailSerializer, self).validate_cluster_type(attrs, ClusterType.TenDBHA)

        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 校验集群与新增proxy云区域是否相同
        super(MysqlProxySwitchDetailSerializer, self).validate_hosts_clusters_in_same_cloud_area(
            attrs, host_key=["origin_proxy", "target_proxy"], cluster_key=["cluster_ids"]
        )

        # 校验角色类型
        super(MysqlProxySwitchDetailSerializer, self).validate_instance_role(
            attrs, instance_key=["origin_proxy"], role=AccessLayer.PROXY
        )

        # 校验替换的proxy的关联集群
        super(MysqlProxySwitchDetailSerializer, self).validate_instance_related_clusters(
            attrs, instance_key=["origin_proxy"], cluster_key=["cluster_ids"], role=AccessLayer.PROXY
        )

        return attrs


class MysqlProxySwitchParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_switch_scene

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["origin_proxy_ip"] = info["origin_proxy"]
            if self.ticket_data["ip_source"] == IpSource.MANUAL_INPUT:
                info["target_proxy_ip"] = info["target_proxy"]


class MysqlProxySwitchResourceParamBuilder(BaseOperateResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            info["target_proxy"] = info.pop("target_proxy")[0]
            info["target_proxy_ip"] = info["target_proxy"]

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_SWITCH)
class MysqlProxySwitchFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlProxySwitchDetailSerializer
    inner_flow_builder = MysqlProxySwitchParamBuilder
    inner_flow_name = _("替换PROXY执行")
    resource_batch_apply_builder = MysqlProxySwitchResourceParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY

    @property
    def need_manual_confirm(self):
        # 需要审批后的人工确认
        return True
