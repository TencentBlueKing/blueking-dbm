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

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbBaseOperateDetailSerializer,
    TendbBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class TendbSpiderAddNodesDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderNodesItemSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        add_spider_role = serializers.ChoiceField(help_text=_("接入层类型"), choices=TenDBClusterSpiderRole.get_choices())
        resource_spec = serializers.DictField(help_text=_("规格参数"))

    ip_source = serializers.ChoiceField(
        help_text=_("机器导入类型"), choices=IpSource.get_choices(), required=False, default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("扩容信息"), child=SpiderNodesItemSerializer())

    def validate(self, attrs):
        super().validate(attrs)
        self.validate_max_spider_master_mnt_count(attrs)
        return attrs


class TendbSpiderAddNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.add_spider_nodes_scene

    def format_ticket_data(self):
        pass


class TendbSpiderAddNodesResourceParamBuilder(TendbBaseOperateResourceParamBuilder):
    def format(self):
        # 在跨机房亲和性要求下，接入层proxy的亲和性要求至少分布在2个机房
        self.patch_info_affinity_location(roles=["spider_ip_list"])
        for info in self.ticket_data["infos"]:
            info["resource_spec"]["spider_ip_list"]["group_count"] = 2

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            # 格式化规格信息
            info["resource_spec"]["spider"] = info["resource_spec"].pop("spider_ip_list")

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_ADD_NODES, is_apply=True)
class TendbSpiderAddNodesFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbSpiderAddNodesDetailSerializer
    inner_flow_builder = TendbSpiderAddNodesFlowParamBuilder
    inner_flow_name = _("TenDBCluster Cluster 接入层扩容")
    resource_batch_apply_builder = TendbSpiderAddNodesResourceParamBuilder
