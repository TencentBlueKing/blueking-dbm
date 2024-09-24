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
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer, HostRecycleSerializer, fetch_cluster_ids
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbSpiderReduceNodesDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderNodesItemSerializer(serializers.Serializer):
        class OldSpiderSerializer(serializers.Serializer):
            spider_reduced_hosts = serializers.ListSerializer(help_text=_("缩容spider信息"), child=HostInfoSerializer())

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        spider_reduced_to_count = serializers.IntegerField(help_text=_("剩余spider数量"), required=False)
        old_nodes = OldSpiderSerializer(help_text=_("缩容指定主机"), required=False)
        reduce_spider_role = serializers.ChoiceField(help_text=_("角色"), choices=TenDBClusterSpiderRole.get_choices())

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"))
    infos = serializers.ListSerializer(help_text=_("缩容信息"), child=SpiderNodesItemSerializer())
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)

    def validate(self, attrs):
        super().validate(attrs)
        self.validate_min_spider_count(attrs)
        return attrs


class TendbSpiderReduceNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.reduce_spider_nodes_scene

    def format_ticket_data(self):
        for info in self.ticket_data:
            info["spider_reduced_hosts"] = info.pop("old_nodes")["spider_reduced_hosts"]


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_REDUCE_NODES, is_recycle=True)
class TendbSpiderReduceNodesFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbSpiderReduceNodesDetailSerializer
    inner_flow_builder = TendbSpiderReduceNodesFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层缩容")
    need_patch_recycle_host_details = True

    def calc_reduce_spider(self):
        """计算实际缩容的spider主机"""
        cluster_ids = fetch_cluster_ids(self.ticket.details["infos"])
        clusters = Cluster.objects.prefetch_related("proxyinstance_set").filter(id__in=cluster_ids)
        cluster_map = {cluster.id: cluster for cluster in clusters}
        for info in self.ticket.details["infos"]:
            # 如果制定主机缩容，则忽略
            if info.get("old_nodes"):
                continue

            cluster = cluster_map[info["cluster_id"]]
            reduce_spider_role = info["reduce_spider_role"]
            # 获取目标角色的spider
            spider_set = [
                proxy
                for proxy in cluster.proxyinstance_set
                if proxy.tendbclusterspiderext.spider_role == reduce_spider_role
            ]
            spider_count = len(spider_set)

            # 计算合理的待下架的spider节点列表
            # 选择上尽量避开ctl_primary的选择, 避免做一次切换逻辑
            ctl_primary_ip = cluster.tendbcluster_ctl_primary_address().split(":")[0]
            except_reduce_spiders = [spider for spider in spider_set if spider.machine.ip != ctl_primary_ip]
            info["old_nodes"]["spider_reduced_hosts"] = [
                {"ip": s.machine.ip, "bk_host_id": s.machine.bk_host_id}
                for s in except_reduce_spiders[: spider_count - reduce_spider_role]
            ]

    def patch_ticket_detail(self):
        self.calc_reduce_spider()
        super().patch_ticket_detail()
