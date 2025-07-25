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


class SpiderSwitchNodesDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderSwitchNodesInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        resource_spec = serializers.DictField(help_text=_("规格参数"))
        row_key = serializers.CharField(help_text=_("唯一值"), required=False)
        switch_spider_role = serializers.ChoiceField(
            help_text=_("接入层类型"), choices=TenDBClusterSpiderRole.get_choices()
        )
        spider_old_ip_list = serializers.JSONField(help_text=_("替换的节点信息"))

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    infos = serializers.ListSerializer(help_text=_("克隆主从信息"), child=SpiderSwitchNodesInfoSerializer())
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    old_nodes = serializers.DictField(help_text=_("旧节点信息集合"), child=serializers.ListField(help_text=_("节点信息")))


class SpiderSwitchNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_switch_nodes_scene
    # 暂时先为空，等校验函数出来再替换
    validator = SpiderController.tendbcluster_switch_nodes_scene.validator


class TendbSpiderSwitchNodesResourceParamBuilder(TendbBaseOperateResourceParamBuilder):
    def format(self):
        # 在跨机房亲和性要求下，接入层proxy的亲和性要求至少分布在2个机房
        self.patch_info_affinity_location()
        for info in self.ticket_data["infos"]:
            role = f'{info["switch_spider_role"]}_{info["spider_old_ip_list"][0]["ip"]}'
            info["resource_spec"][role]["group_count"] = 2

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            # 格式化规格信息
            role = f'{info["switch_spider_role"]}_{info["spider_old_ip_list"][0]["ip"]}'
            info["spider_new_ip_list"] = info.pop(role)
            info["resource_spec"]["spider"] = info["resource_spec"].pop(role)

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_SWITCH_NODES, is_recycle=True)
class SpiderSwitchNodesFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderSwitchNodesDetailSerializer
    inner_flow_builder = SpiderSwitchNodesFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 替换接入层")
    need_patch_recycle_host_details = True
    resource_batch_apply_builder = TendbSpiderSwitchNodesResourceParamBuilder
