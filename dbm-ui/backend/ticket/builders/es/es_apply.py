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

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import ES_DEFAULT_PORT, IpSource
from backend.flow.consts import ES_DEFAULT_INSTANCE_NUM
from backend.flow.engine.controller.es import EsController
from backend.ticket import builders
from backend.ticket.builders.common import constants
from backend.ticket.builders.common.bigdata import BaseEsTicketFlowBuilder, BigDataApplyDetailsSerializer
from backend.ticket.builders.common.constants import BigDataRole
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class EsApplyDetailSerializer(BigDataApplyDetailsSerializer):
    http_port = serializers.IntegerField(help_text=_("端口"), default=ES_DEFAULT_PORT)

    def validate(self, attrs):
        """
        es上架限制:
        1. 主机角色互斥
        2. master数量为>=3的奇数台，通常配置为三台
        3. hot/clod 至少存在一台
        """

        # 判断主机角色是否互斥
        super().validate(attrs)

        # 判断master节点是否为3台
        master_node_count = self.get_node_count(attrs, BigDataRole.Es.MASTER.value)
        if not (master_node_count >= constants.ES_MASTER_NEED and (master_node_count & 1)):
            raise serializers.ValidationError(_("请保证master的部署节点至少为3，且为奇数"))

        # 保证在client存在情况下，存在hot/cold节点
        hot_node_count = self.get_node_count(attrs, BigDataRole.Es.HOT.value)
        cold_node_count = self.get_node_count(attrs, BigDataRole.Es.COLD.value)
        if not (hot_node_count + cold_node_count):
            raise serializers.ValidationError(_("请保证部署至少一台hot/cold节点"))

        return attrs


class EsApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = EsController.es_apply_scene

    def format_ticket_data(self):
        """
        {
            "db_app_abbr": "blueking",
            "bk_biz_id": 2005000002,
            "city_code": "深圳",
            "cluster_name": "cluster",
            "created_by": "admin",
            "db_version": "7.10.2",
            "http_port": 9200,
            "ip_source": "manual_input",
            "domain": "es.cluster_name.blueking.db",
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
                ],
                "master": [
                    {
                        "bk_cloud_id": 0,
                        "bk_host_id": 0,
                        "ip": "127.0.0.7"
                    }
                ]
            },
            "ticket_type": "ES_APPLY",
            "uid": 346
        }
        """
        self.ticket_data.update(
            {
                "username": get_random_string(8),
                "password": get_random_string(16),
                "domain": f"es.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
            }
        )


class EsApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    @classmethod
    def fill_instance_num(cls, next_flow_data, ticket_data, nodes_key):
        """对es的hot和cold角色填充实例数"""
        for role in ["hot", "cold"]:
            if role not in next_flow_data[nodes_key]:
                continue

            for node in next_flow_data["nodes"][role]:
                node["instance_num"] = ticket_data["resource_spec"][role].get("instance_num", ES_DEFAULT_INSTANCE_NUM)

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        self.fill_instance_num(next_flow.details["ticket_data"], self.ticket_data, nodes_key="nodes")
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.ES_APPLY)
class EsApplyFlowBuilder(BaseEsTicketFlowBuilder):
    serializer = EsApplyDetailSerializer
    inner_flow_builder = EsApplyFlowParamBuilder
    inner_flow_name = _("ES集群部署")
    resource_apply_builder = EsApplyResourceParamBuilder
