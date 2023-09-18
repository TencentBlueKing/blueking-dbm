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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.pulsar import PulsarController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BasePulsarTicketFlowBuilder,
    BigDataReplaceDetailSerializer,
    BigDataReplaceResourceParamBuilder,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class PulsarReplaceDetailSerializer(BigDataReplaceDetailSerializer):
    pass


class PulsarReplaceFlowParamBuilder(builders.FlowParamBuilder):
    controller = PulsarController.pulsar_replace_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class PulsarReplaceResourceParamBuilder(BigDataReplaceResourceParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.PULSAR_REPLACE)
class PulsarReplaceFlowBuilder(BasePulsarTicketFlowBuilder):
    serializer = PulsarReplaceDetailSerializer
    inner_flow_builder = PulsarReplaceFlowParamBuilder
    inner_flow_name = _("Pulsar 集群替换")
    resource_apply_builder = PulsarReplaceResourceParamBuilder
