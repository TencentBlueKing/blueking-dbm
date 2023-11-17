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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TbinlogdumperSwitchNodesDetailSerializer(serializers.Serializer):
    class DumperSwitchInfoSerializer(serializers.Serializer):
        class SwitchInstanceSerializer(serializers.Serializer):
            host = serializers.CharField(help_text=_("主机IP"))
            port = serializers.IntegerField(help_text=_("主机端口"))
            repl_binlog_file = serializers.CharField(help_text=_("待切换后需要同步的binlog文件"))
            repl_binlog_pos = serializers.IntegerField(help_text=_("待切换后需要同步的binlog文件的为位点"))

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        switch_instances = serializers.ListSerializer(help_text=_("dumper切换信息"), child=SwitchInstanceSerializer())

    infos = serializers.ListSerializer(child=DumperSwitchInfoSerializer())
    is_safe = serializers.BooleanField(help_text=_("是否安全切换"), required=False, default=True)


class TbinlogdumperSwitchNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = TBinlogDumperController.switch_nodes_scene


@builders.BuilderFactory.register(TicketType.TBINLOGDUMPER_SWITCH_NODES)
class TbinlogdumperSwitchNodesFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TbinlogdumperSwitchNodesDetailSerializer
    inner_flow_builder = TbinlogdumperSwitchNodesFlowParamBuilder
    inner_flow_name = _("Tbinlogdumper 切换")
