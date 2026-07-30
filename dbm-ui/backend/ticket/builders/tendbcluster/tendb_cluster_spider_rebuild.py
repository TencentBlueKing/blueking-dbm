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
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.flow.engine.controller.spider import SpiderController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder
from backend.ticket.builders.tendbcluster.base import TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbClusterSpiderRebuildDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderClusterInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群 ID"), required=True)
        spider_ip_list = serializers.ListField(help_text=_("待重建的 Spider IP 列表"), child=serializers.DictField())
        rebuild_spider_role = serializers.CharField(max_length=128, help_text=_("重建的 Spider 角色"))

    infos = serializers.ListField(help_text=_("重建 Spider 实例列表"), child=SpiderClusterInfoSerializer())

    def to_representation(self, instance):
        return instance


class TendbClusterSpiderRebuildParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.rebuild_spider_nodes_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_REBUILD, iam=ActionEnum.TENDBCLUSTER_MANAGE)
class TendbClusterSpiderRebuildFlowBuilder(BaseMySQLHATicketFlowBuilder):
    group = DBType.TenDBCluster.value
    serializer = TendbClusterSpiderRebuildDetailSerializer
    inner_flow_builder = TendbClusterSpiderRebuildParamBuilder
    inner_flow_name = _("TenDBCluster 接入层原地重建")
    validator = SpiderController.rebuild_spider_nodes_scene.validator
