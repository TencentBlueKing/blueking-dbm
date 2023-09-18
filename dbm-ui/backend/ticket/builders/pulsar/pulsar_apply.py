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
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.pulsar import PulsarController
from backend.ticket import builders
from backend.ticket.builders.common import constants
from backend.ticket.builders.common.bigdata import BasePulsarTicketFlowBuilder, BigDataApplyDetailsSerializer
from backend.ticket.builders.common.constants import BigDataRole
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class PulsarApplyDetailSerializer(BigDataApplyDetailsSerializer):
    replication_num = serializers.IntegerField(help_text=_("副本数量"))
    partition_num = serializers.IntegerField(help_text=_("分区数量"))
    retention_hours = serializers.IntegerField(help_text=_("保留时长（小时）"))
    ack_quorum = serializers.IntegerField(help_text=_("至少写入成功副本数"))
    port = serializers.IntegerField(help_text=_("端口"))

    def validate(self, attrs):
        """
        pulsar上架限制:
        1. 主机角色互斥
        2. bookkeeper节点至少两台
        3. zookeeper节点需要三台
        4. broker节点至少1台
        5. 副本数量至少为2，且不超过bookkeeper数量
        6. 最小成功写入副本数量<=副本数量
        """

        # 判断主机角色是否互斥
        super().validate(attrs)
        replication_num = attrs["replication_num"]
        ack_quorum = attrs["replication_num"]

        # 判断bookkeeper节点是否至少为2台
        bookkeeper_node_count = self.get_node_count(attrs, BigDataRole.Pulsar.BOOKKEEPER.value)
        if bookkeeper_node_count < constants.PULSAR_BOOKKEEPER_MIN:
            raise serializers.ValidationError(_("bookkeeper节点数小于2台! 请保证bookkeeper的部署节点数至少为2"))

        # 判断zookeeper节点是3台
        zookeeper_node_count = self.get_node_count(attrs, BigDataRole.Pulsar.ZOOKEEPER.value)
        if zookeeper_node_count != constants.PULSAR_ZOOKEEPER_NEED:
            raise serializers.ValidationError(_("zookeeper节点数不为3台! 请保证zookeeper的部署节点数等于为3"))

        # 判断broker节点是1台
        broker_node_count = self.get_node_count(attrs, BigDataRole.Pulsar.BROKER.value)
        if broker_node_count < constants.PULSAR_BROKER_MIN:
            raise serializers.ValidationError(_("broker节点数小于1台! 请保证broker的部署节点数至少为1"))

        # 副本数量至少为2，且不超过bookkeeper数量
        if replication_num < constants.PULSAR_REPLICATION_NUM_MIN or replication_num > bookkeeper_node_count:
            raise serializers.ValidationError(_("请保证副本数量至少为2，且不超过bookkeeper数量"))

        if ack_quorum > replication_num:
            raise serializers.ValidationError(_("最小成功写入副本数量不得大于副本数量"))

        return attrs


class PulsarApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = PulsarController.pulsar_apply_scene

    def format_ticket_data(self):
        # TODO: 暂时先生成随机的账号密码
        self.ticket_data.update(
            {
                "username": get_random_string(8),
                "password": get_random_string(16),
                "domain": f"pulsar.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
            }
        )


class PulsarApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.PULSAR_APPLY)
class PulsarApplyFlowBuilder(BasePulsarTicketFlowBuilder):
    serializer = PulsarApplyDetailSerializer
    inner_flow_builder = PulsarApplyFlowParamBuilder
    inner_flow_name = _("Pulsar 集群部署")
    resource_apply_builder = PulsarApplyResourceParamBuilder
