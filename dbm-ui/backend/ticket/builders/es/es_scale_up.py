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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.es import EsController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BaseEsTicketFlowBuilder,
    BigDataScaleDetailSerializer,
    BigDataScaleUpResourceParamBuilder,
)
from backend.ticket.builders.es.es_apply import EsApplyResourceParamBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class EsScaleUpDetailSerializer(BigDataScaleDetailSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)

        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        role_nodes_list = list(attrs["nodes"].values())

        node_list = []
        for role_nodes in role_nodes_list:
            node_list.extend(role_nodes)

        min_instance_num = min([node["instance_num"] for node in node_list if "instance_num" in node.keys()])
        if min_instance_num <= 0:
            raise serializers.ValidationError(_("实例数必须为正数，请确保实例的合法性"))

        return attrs


class EsScaleUpResourceParamBuilder(BigDataScaleUpResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        EsApplyResourceParamBuilder.fill_instance_num(
            next_flow.details["ticket_data"], self.ticket_data, nodes_key="nodes"
        )
        next_flow.save(update_fields=["details"])


class EsScaleUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = EsController.es_scale_up_scene

    def format_ticket_data(self):
        """
        {
            "uid": 346,
            "ticket_type": "ES_SCALE_UP",
            "bk_biz_id": 2005000002,
            "created_by": "admin",
            "cluster_id": 123,
            "nodes": {
                "client": [
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


@builders.BuilderFactory.register(TicketType.ES_SCALE_UP)
class EsScaleUpFlowBuilder(BaseEsTicketFlowBuilder):
    serializer = EsScaleUpDetailSerializer
    inner_flow_builder = EsScaleUpFlowParamBuilder
    inner_flow_name = _("ES集群扩容")
    resource_apply_builder = EsScaleUpResourceParamBuilder
