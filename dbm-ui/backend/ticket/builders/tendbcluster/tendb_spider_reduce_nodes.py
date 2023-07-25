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

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbBaseOperateDetailSerializer,
    TendbBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class TendbSpiderReduceNodesDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderNodesItemSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        spider_reduced_to_count = serializers.IntegerField(help_text=_("剩余spider数量"))
        reduce_spider_role = serializers.ChoiceField(
            help_text=_("缩容的角色"), choices=TenDBClusterSpiderRole.get_choices()
        )

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"))
    infos = serializers.ListSerializer(help_text=_("缩容信息"), child=SpiderNodesItemSerializer())


class TendbSpiderReduceNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.reduce_spider_nodes_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_REDUCE_NODES, is_apply=True)
class TendbSpiderReduceNodesFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbSpiderReduceNodesDetailSerializer
    inner_flow_builder = TendbSpiderReduceNodesFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层缩容")

    @property
    def need_itsm(self):
        return False
