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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.doris import DorisController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BaseDorisTicketFlowBuilder,
    BigDataScaleDetailSerializer,
    BigDataScaleUpResourceParamBuilder,
)
from backend.ticket.builders.doris.doris_apply import DorisApplyResourceParamBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisScaleUpDetailSerializer(BigDataScaleDetailSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)

        # 存储角色对应的扩容数量
        count_stats = {}
        for key, value in attrs["resource_spec"].items():
            extra = "doris_" if key == "observer" else "doris_backend_"
            count_stats[extra + key] = value.get("count", 0)

        cluster = Cluster.objects.get(id=attrs["cluster_id"])

        # 获取集群所有角色信息
        exist_storages = cluster.storageinstance_set.filter(
            instance_role__in=[
                InstanceRole.DORIS_BACKEND_HOT,
                InstanceRole.DORIS_BACKEND_COLD,
                InstanceRole.DORIS_OBSERVER,
            ]
        )

        # 创建一个包含角色及其最低节点数量要求的元组列表
        role_min_count_pairs = [
            (InstanceRole.DORIS_OBSERVER, _("请保证扩容的observer节点的角色总和最小值为2以上")),
            (InstanceRole.DORIS_BACKEND_COLD, _("请保证扩容的cold节点的角色总和最小值为2以上")),
            (InstanceRole.DORIS_BACKEND_HOT, _("请保证扩容的hot节点的角色总和最小值为2以上")),
        ]

        # 验证角色节点数量
        for role, error_message in role_min_count_pairs:
            if role.value in count_stats:
                exist_hosts = {
                    storage.machine.bk_host_id for storage in exist_storages if storage.instance_role == role
                }
                node_count = len(exist_hosts) + count_stats[role.value]
                if node_count < 2:
                    raise serializers.ValidationError(error_message)

        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        role_nodes_list = list(attrs["nodes"].values())

        node_list = []
        for role_nodes in role_nodes_list:
            node_list.extend(role_nodes)

        instance_num_list = [node["instance_num"] for node in node_list if "instance_num" in node.keys()]
        if instance_num_list and min(instance_num_list) <= 0:
            raise serializers.ValidationError(_("实例数必须为正数，请确保实例的合法性"))

        return attrs


class DorisScaleUpResourceParamBuilder(BigDataScaleUpResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        DorisApplyResourceParamBuilder.fill_instance_num(
            next_flow.details["ticket_data"], self.ticket_data, nodes_key="nodes"
        )
        next_flow.save(update_fields=["details"])


class DorisScaleUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_scale_up_scene

    def format_ticket_data(self):
        """
        {
            "uid": 346,
            "ticket_type": "DORIS_SCALE_UP",
            "bk_biz_id": 2005000002,
            "created_by": "admin",
            "cluster_id": 123,
            "nodes": {
                "observer": [
                    {
                        "bk_cloud_id": 0,
                        "bk_host_id": 0,
                        "ip": "127.0.0.7"
                    }
                ],
                "cold": [
                    {
                        "bk_cloud_id": 0,
                        "bk_host_id": 0,
                        "instance_num": 1,
                        "ip": "127.0.0.2"
                    }
                ],
                "hot": [
                    {
                        "bk_cloud_id": 0,
                        "bk_host_id": 0,
                        "instance_num": 1,
                        "ip": "127.0.0.1"
                    }
                ]
            },
        }
        """
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.DORIS_SCALE_UP, is_apply=True)
class DorisScaleUpFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisScaleUpDetailSerializer
    inner_flow_builder = DorisScaleUpFlowParamBuilder
    inner_flow_name = _("Doris集群扩容")
    resource_apply_builder = DorisScaleUpResourceParamBuilder
