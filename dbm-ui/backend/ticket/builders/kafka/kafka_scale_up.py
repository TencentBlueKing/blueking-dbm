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

from backend.flow.engine.controller.kafka import KafkaController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BaseKafkaTicketFlowBuilder,
    BigDataScaleDetailSerializer,
    BigDataScaleUpResourceParamBuilder,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class KafkaScaleUpDetailSerializer(BigDataScaleDetailSerializer):
    pass


class KafkaScaleUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = KafkaController.kafka_scale_up_scene

    def format_ticket_data(self):
        """
        {
            "uid": 346,
            "ticket_type": "KAFKA_SCALE_UP",
            "bk_biz_id": 2005000002,
            "created_by": "admin",
            "cluster_id": 123,
            "nodes": {
                "broker": [
                    {
                        "bk_cloud_id": 0,
                        "bk_host_id": 0,
                        "ip": "127.0.0.7"
                    }
                ]
            },
        }
        """
        super().format_ticket_data()


class KafkaScaleUpResourceParamBuilder(BigDataScaleUpResourceParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.KAFKA_SCALE_UP, is_apply=True)
class KafkaScaleUpFlowBuilder(BaseKafkaTicketFlowBuilder):
    serializer = KafkaScaleUpDetailSerializer
    inner_flow_builder = KafkaScaleUpFlowParamBuilder
    inner_flow_name = _("Kafka 集群扩容")
    resource_apply_builder = KafkaScaleUpResourceParamBuilder
