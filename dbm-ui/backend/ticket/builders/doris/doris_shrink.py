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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.doris import DorisController
from backend.ticket import builders
from backend.ticket.builders.common import constants
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.common.bigdata import BaseDorisTicketFlowBuilder, BigDataSingleClusterOpsDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisShrinkDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    # 目前只支持hot/cold/observer节点缩容，不支持follower节点缩容
    class NodesSerializer(serializers.Serializer):
        hot = serializers.ListField(help_text=_("hot信息列表"), child=serializers.DictField())
        cold = serializers.ListField(help_text=_("cold信息列表"), child=serializers.DictField())
        observer = serializers.ListField(help_text=_("observer信息列表"), child=serializers.DictField())

    old_nodes = NodesSerializer(help_text=_("nodes节点列表"))
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)

    def validate(self, attrs):
        super().validate(attrs)

        role_hash = {
            InstanceRole.DORIS_BACKEND_HOT: attrs["old_nodes"]["hot"],
            InstanceRole.DORIS_BACKEND_COLD: attrs["old_nodes"]["cold"],
            InstanceRole.DORIS_OBSERVER: attrs["old_nodes"]["observer"],
        }

        cluster = Cluster.objects.get(id=attrs["cluster_id"])

        # 获取集群所有角色信息
        exist_storages = cluster.storageinstance_set.filter(
            instance_role__in=[
                InstanceRole.DORIS_BACKEND_HOT,
                InstanceRole.DORIS_BACKEND_COLD,
                InstanceRole.DORIS_OBSERVER,
            ]
        )

        # observer缩容最小值为0或2
        shrink_observer_hosts = {host["bk_host_id"] for host in role_hash[InstanceRole.DORIS_OBSERVER]}
        exist_observer_hosts = set(
            [
                storage.machine.bk_host_id
                for storage in exist_storages
                if storage.instance_role == InstanceRole.DORIS_OBSERVER
            ]
        )
        observer_node_count = len(exist_observer_hosts - shrink_observer_hosts)
        if not (
            observer_node_count == constants.DORIS_OBSERVER_ZERO or observer_node_count >= constants.DORIS_OBSERVER_MIN
        ):
            raise serializers.ValidationError(_("请保证部署的observer节点的角色最小值为0或2以上"))

        # hot，cold必须有一个角色，每个角色至少需要2个节点
        shrink_hot_hosts = {host["bk_host_id"] for host in role_hash[InstanceRole.DORIS_BACKEND_HOT]}
        shrink_cold_hosts = {host["bk_host_id"] for host in role_hash[InstanceRole.DORIS_BACKEND_COLD]}
        exist_hot_hosts = set(
            [
                storage.machine.bk_host_id
                for storage in exist_storages
                if storage.instance_role == InstanceRole.DORIS_BACKEND_HOT
            ]
        )
        exist_cold_hosts = set(
            [
                storage.machine.bk_host_id
                for storage in exist_storages
                if storage.instance_role == InstanceRole.DORIS_BACKEND_COLD
            ]
        )
        hot_node_count = len(exist_hot_hosts - shrink_hot_hosts)
        cold_node_count = len(exist_cold_hosts - shrink_cold_hosts)
        total_nodes = hot_node_count + cold_node_count
        if not total_nodes:
            raise serializers.ValidationError(_("请保证冷/热节点必选1种以上"))
        if not (hot_node_count >= constants.DORIS_HOT_COLD_LIMIT or cold_node_count >= constants.DORIS_HOT_COLD_LIMIT):
            raise serializers.ValidationError(_("请保证部署的冷/热节点的角色为2以上"))

        # 不允许缩容follower节点
        all_shrink_hosts = {host["bk_host_id"] for role in role_hash for host in role_hash[role]}
        all_exist_storages = cluster.storageinstance_set.exclude(instance_role=InstanceRole.DORIS_FOLLOWER)
        all_exist_hosts = all_exist_storages.values_list("machine__bk_host_id", flat=True)

        if not set(all_exist_hosts).issuperset(set(all_shrink_hosts)):
            raise serializers.ValidationError(_("缩容仅支持hot、cold和observer"))

        return attrs


class DorisShrinkFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_shrink_scene

    def format_ticket_data(self):
        self.ticket_data["nodes"] = self.ticket_data.pop("old_nodes")
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.DORIS_SHRINK, is_recycle=True)
class DorisShrinkFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisShrinkDetailSerializer
    inner_flow_builder = DorisShrinkFlowParamBuilder
    inner_flow_name = _("Doris集群缩容")
    need_patch_recycle_host_details = True
