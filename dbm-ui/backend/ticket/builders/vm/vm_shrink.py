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
from rest_framework import serializers

from backend.flow.engine.controller.vm import VmController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseVmTicketFlowBuilder, BigDataSingleClusterOpsDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class VmShrinkDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    # 目前只支持hot/cold/client节点缩容，不支持master节点缩容
    class NodesSerializer(serializers.Serializer):
        hot = serializers.ListField(help_text=_("hot信息列表"), child=serializers.DictField())
        cold = serializers.ListField(help_text=_("cold信息列表"), child=serializers.DictField())
        client = serializers.ListField(help_text=_("client信息列表"), child=serializers.DictField())

    nodes = NodesSerializer(help_text=_("nodes节点列表"))

    def validate(self, attrs):
        super().validate(attrs)
        return attrs


class VmShrinkFlowParamBuilder(builders.FlowParamBuilder):
    controller = VmController.vm_shrink_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.VM_SHRINK)
class EsShrinkFlowBuilder(BaseVmTicketFlowBuilder):
    serializer = VmShrinkDetailSerializer
    inner_flow_builder = VmShrinkFlowParamBuilder
    inner_flow_name = _("VictoriaMetrics 集群缩容")
