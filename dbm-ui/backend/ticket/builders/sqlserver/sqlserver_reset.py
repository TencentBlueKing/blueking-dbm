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

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class SQLServerResetDetailSerializer(MySQLBaseOperateDetailSerializer):
    class ResetInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        new_cluster_name = serializers.CharField(help_text=_("重置集群名"))
        new_immutable_domain = serializers.CharField(help_text=_("重置集群主域名"))
        new_slave_domain = serializers.CharField(help_text=_("重置集群从域名"))

    infos = serializers.ListField(help_text=_("集群重置信息"), child=ResetInfoSerializer())

    def validate(self, attrs):
        # 校验所有集群都处于禁用状态
        clusters = Cluster.objects.filter(id__in=fetch_cluster_ids(attrs))
        for cluster in clusters:
            if cluster.phase != ClusterPhase.OFFLINE.value:
                raise serializers.ValidationError(_("集群:{}不处于禁用态，无法重置").format(cluster.name))
        return attrs


class SQLServerResetFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.cluster_reset_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.SQLSERVER_RESET)
class SQLServerResetFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = SQLServerResetDetailSerializer
    inner_flow_builder = SQLServerResetFlowParamBuilder
    inner_flow_name = _("SQLServer 集群重置执行")
