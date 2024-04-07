# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import logging

from django.utils.translation import gettext as _

from backend.flow.engine.controller.pulsar import PulsarController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BasePulsarTicketFlowBuilder, BigDataRebootDetailSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class PulsarRebootDetailSerializer(BigDataRebootDetailSerializer):
    pass


class PulsarRebootFlowParamBuilder(builders.FlowParamBuilder):
    controller = PulsarController.pulsar_reboot_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.PULSAR_REBOOT)
class PulsarRebootFlowBuilder(BasePulsarTicketFlowBuilder):
    serializer = PulsarRebootDetailSerializer
    inner_flow_builder = PulsarRebootFlowParamBuilder
    inner_flow_name = _("Pulsar 集群重启")
