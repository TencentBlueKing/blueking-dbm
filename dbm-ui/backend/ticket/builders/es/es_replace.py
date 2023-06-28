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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.es import EsController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BaseEsTicketFlowBuilder,
    BigDataReplaceDetailSerializer,
    BigDataReplaceResourceParamBuilder,
)
from backend.ticket.builders.es.es_apply import EsApplyResourceParamBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class EsReplaceDetailSerializer(BigDataReplaceDetailSerializer):
    pass


class EsReplaceFlowParamBuilder(builders.FlowParamBuilder):
    controller = EsController.es_replace_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class EsReplaceResourceParamBuilder(BigDataReplaceResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        EsApplyResourceParamBuilder.fill_instance_num(
            next_flow.details["ticket_data"], self.ticket_data, nodes_key="new_nodes"
        )
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.ES_REPLACE)
class EsReplaceFlowBuilder(BaseEsTicketFlowBuilder):
    serializer = EsReplaceDetailSerializer
    inner_flow_builder = EsReplaceFlowParamBuilder
    inner_flow_name = _("ES集群替换")
    resource_apply_builder = EsReplaceResourceParamBuilder
