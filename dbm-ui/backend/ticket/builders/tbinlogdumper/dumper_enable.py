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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.tendbcluster.base import BaseDumperTicketFlowBuilder
from backend.ticket.constants import TicketType


class TbinlogdumperEnableDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    dumper_instance_ids = serializers.ListField(help_text=_("dumper实例ID"), child=serializers.IntegerField())


class TbinlogdumperEnableFlowParamBuilder(builders.FlowParamBuilder):
    controller = TBinlogDumperController.enable_nodes_scene

    def format_ticket_data(self):
        self.ticket_data["enable_ids"] = self.ticket_data.pop("dumper_instance_ids")


@builders.BuilderFactory.register(TicketType.TBINLOGDUMPER_ENABLE_NODES, iam=ActionEnum.TBINLOGDUMPER_ENABLE_DISABLE)
class TbinlogdumperEnableFlowBuilder(BaseDumperTicketFlowBuilder):
    serializer = TbinlogdumperEnableDetailSerializer
    inner_flow_builder = TbinlogdumperEnableFlowParamBuilder
    inner_flow_name = _("Tbinlogdumper 启用")
