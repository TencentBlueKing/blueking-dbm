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

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import KAFKA_DEFAULT_PORT, IpSource
from backend.flow.engine.controller.kafka import KafkaController
from backend.ticket import builders
from backend.ticket.builders.common import constants
from backend.ticket.builders.common.bigdata import BaseKafkaTicketFlowBuilder, BigDataApplyDetailsSerializer
from backend.ticket.builders.common.constants import BigDataRole
from backend.ticket.constants import TicketType


class KafkaApplyDetailSerializer(BigDataApplyDetailsSerializer):
    """
    {
        "username": "username",
        "uid": 352,
        "ticket_type": "KAFKA_APPLY",
        "retention_hours": 2,
        "replication_num": 2,
        "port": 9200,
        "password": "password",
        "partition_num": 2,
        "no_security": 0,
        "nodes": {
            "zookeeper": [
                {
                    "ip": "127.0.0.1",
                    "bk_cloud_id": 0
                },
                {
                    "ip": "127.0.0.2",
                    "bk_cloud_id": 0
                },
                {
                    "ip": "127.0.0.3",
                    "bk_cloud_id": 0
                }
            ],
            "broker": [
                {
                    "ip": "127.0.0.3",
                    "bk_cloud_id": 0
                },
                {
                    "ip": "127.0.0.4",
                    "bk_cloud_id": 0
                }
            ]
        },
        "ip_source": "manual_input",
        "db_version": "133",
        "created_by": "admin",
        "cluster_name": "kafka-cluster",
        "city_code": "深圳",
        "bk_biz_id": 2005000002,
        "db_app_abbr": "blueking"
    }
    """

    no_security = serializers.IntegerField(
        help_text=_("无认证开关, 1表示无认证。0表示认证，默认0"), min_value=0, max_value=1, required=False, default=0
    )
    replication_num = serializers.IntegerField(
        help_text=_("副本数量"),
    )
    partition_num = serializers.IntegerField(
        help_text=_("分区数量"),
    )
    retention_hours = serializers.IntegerField(
        help_text=_("保留时长（小时）"),
    )
    port = serializers.IntegerField(help_text=_("端口"), default=KAFKA_DEFAULT_PORT)

    # TODO: 暂时不涉及账号密码
    # username = serializers.CharField(help_text="用户名")
    # password = serializers.CharField(help_text="密码")

    def validate(self, attrs):
        """
        kafka上架限制：
        1. 主机角色互斥
        2. zk的数量固定为3台
        3. broker至少为1台，副本数量小于等于broker数量
        """

        # 判断主机角色是否互斥
        super().validate(attrs)

        # 判断zookeeper数量固定为3
        zookeeper_node_count = self.get_node_count(attrs, BigDataRole.Kafka.ZOOKEEPER.value)
        if zookeeper_node_count != constants.KAFKA_ZOOKEEPER_NEED:
            raise serializers.ValidationError(_("Zookeeper节点数量不等于3台，请确保Zookeeper节点数量为3"))

        # 判断broker数量以及与副本数量的关系
        replication_num = attrs["replication_num"]
        broker_node_count = self.get_node_count(attrs, BigDataRole.Kafka.BROKER.value)
        if broker_node_count < constants.KAFKA_BROKER_MIN or replication_num > broker_node_count:
            raise serializers.ValidationError(_("Broker节点与副本节点数量有误，请确保Broker节点至少为1且副本数量<=Broker数量"))

        return attrs


class KafkaApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = KafkaController.kafka_apply_scene

    def format_ticket_data(self):
        self.ticket_data.update(
            {
                "username": get_random_string(8),
                "password": get_random_string(16),
                "domain": f"kafka.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
            }
        )


class KafkaApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.KAFKA_APPLY)
class KafkaApplyFlowBuilder(BaseKafkaTicketFlowBuilder):
    serializer = KafkaApplyDetailSerializer
    inner_flow_builder = KafkaApplyFlowParamBuilder
    inner_flow_name = _("Kafka 集群部署")
    resource_apply_builder = KafkaApplyResourceParamBuilder
