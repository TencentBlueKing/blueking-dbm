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

from backend.flow.engine.controller.doris import DorisController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseDorisTicketFlowBuilder, BigDataSingleClusterOpsDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisShrinkDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    # 目前只支持hot/warm/observer节点缩容，不支持follower节点缩容
    class NodesSerializer(serializers.Serializer):
        hot = serializers.ListField(help_text=_("hot信息列表"), child=serializers.DictField())
        warm = serializers.ListField(help_text=_("warm信息列表"), child=serializers.DictField())
        observer = serializers.ListField(help_text=_("observer信息列表"), child=serializers.DictField())

    old_nodes = NodesSerializer(help_text=_("nodes节点列表"))


class DorisShrinkFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_shrink_scene

    def format_ticket_data(self):
        self.ticket_data["nodes"] = self.ticket_data.pop("old_nodes")
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.DORIS_SHRINK, is_recycle=True, iam=ActionEnum.DORIS_MANAGE)
class DorisShrinkFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisShrinkDetailSerializer
    inner_flow_builder = DorisShrinkFlowParamBuilder
    inner_flow_name = _("Doris集群缩容")
    need_patch_recycle_host_details = True
