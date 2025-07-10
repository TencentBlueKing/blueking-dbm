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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.flow.engine.controller.kafka import KafkaController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseKafkaTicketFlowBuilder, BigDataDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class KafkaRebalanceDetailSerializer(BigDataDetailsSerializer):
    class OldProxySerializer(serializers.Serializer):
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        ip = serializers.CharField(help_text=_("IP地址"))
        bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
        port = serializers.IntegerField(help_text=_("端口"))

    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    topics = serializers.ListField(help_text=_("topics"), child=serializers.CharField())
    throttle_rate = serializers.IntegerField(help_text=_("要均衡的速率"))
    instance_list = serializers.ListField(help_text=_("broker 列表"), child=OldProxySerializer())
    instance_info = serializers.JSONField(help_text=_("前端展示实例信息"), required=False)


class KafkaRebalanceFlowParamBuilder(builders.FlowParamBuilder):
    controller = KafkaController.kafka_rebalance_scene


@builders.BuilderFactory.register(TicketType.KAFKA_REBALANCE)
class KafkaRebalanceFlowBuilder(BaseKafkaTicketFlowBuilder):
    serializer = KafkaRebalanceDetailSerializer
    inner_flow_builder = KafkaRebalanceFlowParamBuilder
    inner_flow_name = _("Kafka Topic 均衡")
