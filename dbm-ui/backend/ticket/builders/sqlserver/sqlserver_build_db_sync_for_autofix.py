"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging.config

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import Cluster
from backend.db_monitor.serializers import AlarmCallBackDataSerializer
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType

logger = logging.getLogger("flow")


class SQLServerBuildDBSyncForAutofixSerializer(AlarmCallBackDataSerializer):
    """
    接收告警事件,确认是否要做自动同步
    """

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        dimensions = data["callback_message"]["event"]["dimensions"]
        cluster = Cluster.objects.get(immute_domain=dimensions["cluster_domain"])
        ticket_detail = {"infos": [{"cluster_id": cluster.id, "sync_dbs": []}]}
        return ticket_detail


class SQLServerBuildDBSyncForSerializer(SQLServerBaseOperateDetailSerializer):
    class BuildDBSyncInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        sync_dbs = serializers.ListField(help_text=_("同步的数据库"), required=False, default=[])

    infos = serializers.ListSerializer(help_text=_("同步信息列表"), child=BuildDBSyncInfoSerializer())

    def validate(self, attrs):
        """验证库表数据库的数据"""
        super().validate(attrs)
        return attrs


class SQLServerClearFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.ha_build_db_sync_scene


@builders.BuilderFactory.register(TicketType.SQLSERVER_BUILD_DB_SYNC, is_apply=False)
class SQLServerClearFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerBuildDBSyncForAutofixSerializer
    alarm_transform_serializer = SQLServerBuildDBSyncForAutofixSerializer
    inner_flow_builder = SQLServerClearFlowParamBuilder
    inner_flow_name = _("SQLServer 同步数据")
    retry_type = FlowRetryType.MANUAL_RETRY
