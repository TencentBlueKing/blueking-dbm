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
from backend.flow.engine.controller.kafka import KafkaController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseKafkaTicketFlowBuilder, BigDataSingleClusterOpsDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class KafkaShrinkDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):

    # 目前只支持broker节点缩容
    class NodesSerializer(serializers.Serializer):
        broker = serializers.ListField(help_text=_("broker信息列表"), child=serializers.DictField())

    nodes = NodesSerializer(help_text=_("nodes节点信息"))

    def validate(self, attrs):
        super().validate(attrs)

        role_hash = {
            InstanceRole.BROKER: attrs["nodes"]["broker"],
        }

        cluster = Cluster.objects.get(id=attrs["cluster_id"])

        all_shrink_hosts = []
        all_exist_hosts = []
        for role in [InstanceRole.BROKER]:
            shrink_hosts = {host["bk_host_id"] for host in role_hash[role]}
            exist_hosts = set(
                cluster.storageinstance_set.filter(instance_role=role).values_list("machine__bk_host_id", flat=True)
            )

            all_shrink_hosts.extend(shrink_hosts)
            all_exist_hosts.extend(exist_hosts)

            # TODO: 需要比对副本数配置(broker数>=副本数)，目前无法获取到
            keep_hosts = exist_hosts - shrink_hosts
            if len(keep_hosts) < 1:
                raise serializers.ValidationError(_("{}: 至少保留1台!").format(role.name))

        if not set(all_exist_hosts).issuperset(set(all_shrink_hosts)):
            raise serializers.ValidationError(_("缩容仅支持Broker"))

        return attrs


class KafkaShrinkFlowParamBuilder(builders.FlowParamBuilder):
    controller = KafkaController.kafka_shrink_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.KAFKA_SHRINK)
class KafkaShrinkFlowBuilder(BaseKafkaTicketFlowBuilder):
    serializer = KafkaShrinkDetailSerializer
    inner_flow_builder = KafkaShrinkFlowParamBuilder
    inner_flow_name = _("Kafka 集群缩容")
