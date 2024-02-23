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

from django.utils.translation import gettext as _

from backend.flow.engine.controller.pulsar import PulsarController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BasePulsarTicketFlowBuilder,
    BigDataScaleDetailSerializer,
    BigDataScaleUpResourceParamBuilder,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class PulsarScaleUpDetailSerializer(BigDataScaleDetailSerializer):
    pass


class PulsarScaleUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = PulsarController.pulsar_scale_up_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class PulsarScaleUpResourceParamBuilder(BigDataScaleUpResourceParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.PULSAR_SCALE_UP, is_apply=True)
class PulsarScaleUpFlowBuilder(BasePulsarTicketFlowBuilder):
    serializer = PulsarScaleUpDetailSerializer
    inner_flow_builder = PulsarScaleUpFlowParamBuilder
    inner_flow_name = _("Pulsar 集群扩容")
    resource_apply_builder = PulsarScaleUpResourceParamBuilder
