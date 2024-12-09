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

from backend.flow.engine.controller.doris import DorisController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BaseDorisTicketFlowBuilder,
    BigDataReplaceDetailSerializer,
    BigDataReplaceResourceParamBuilder,
)
from backend.ticket.builders.doris.doris_apply import DorisApplyResourceParamBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisReplaceDetailSerializer(BigDataReplaceDetailSerializer):
    pass


class DorisReplaceFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_replace_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class DorisReplaceResourceParamBuilder(BigDataReplaceResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        DorisApplyResourceParamBuilder.fill_instance_num(
            next_flow.details["ticket_data"], self.ticket_data, nodes_key="nodes"
        )
        next_flow.details["ticket_data"]["new_nodes"] = next_flow.details["ticket_data"].pop("nodes")
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.DORIS_REPLACE, is_apply=True, is_recycle=True)
class DorisReplaceFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisReplaceDetailSerializer
    inner_flow_builder = DorisReplaceFlowParamBuilder
    inner_flow_name = _("DORIS集群替换")
    resource_apply_builder = DorisReplaceResourceParamBuilder
    need_patch_recycle_host_details = True
