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

from backend.flow.consts import TBinlogDumperAddType
from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TbinlogdumperApplyDetailSerializer(serializers.Serializer):
    class DumperInfoSerializer(serializers.Serializer):
        class AddInfoSerializer(serializers.Serializer):
            area_name = serializers.IntegerField(help_text=_("dumper安装的大区"))
            module_id = serializers.IntegerField(help_text=_("dumper的模块"))
            add_type = serializers.ChoiceField(help_text=_("dumper的安装方式"), choices=TBinlogDumperAddType.get_choices())

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        add_infos = serializers.ListSerializer(help_text=_("dumper部署信息"), child=AddInfoSerializer())

    infos = serializers.ListSerializer(child=DumperInfoSerializer())


class TbinlogdumperApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = TBinlogDumperController.add_nodes_scene


@builders.BuilderFactory.register(TicketType.TBINLOGDUMPER_INSTALL)
class TbinlogdumperApplyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TbinlogdumperApplyDetailSerializer
    inner_flow_builder = TbinlogdumperApplyFlowParamBuilder
    inner_flow_name = _("Tbinlogdumper 上架")
