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


class SQLServerDownForAutoFixSerializer(AlarmCallBackDataSerializer):
    """
    接收sqlserver_service状态告警事件，处理自愈逻辑
    目前会对未接入dbha的实例，修复实例状态
    """

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        dimensions = data["callback_message"]["event"]["dimensions"]
        cluster = Cluster.objects.get(immute_domain=dimensions["cluster_domain"])
        ip = dimensions["instance"].split("-")[0]
        ticket_detail = {"infos": [{"cluster_id": cluster.id, "ip_list": [ip]}]}
        return ticket_detail


class SQLServerModifyInstStatusSerializer(SQLServerBaseOperateDetailSerializer):
    class ModifyInstStatusSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        ip_list = serializers.ListField(help_text=_("待修改主机ip"), required=True)

    infos = serializers.ListSerializer(help_text=_("实例修改列表"), child=ModifyInstStatusSerializer())

    def validate(self, attrs):
        """验证库表数据库的数据"""
        super().validate(attrs)
        return attrs


class SQLServerModifyInstStatusParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.sqlserver_modify_inst_status_scene


@builders.BuilderFactory.register(TicketType.SQLSERVER_MODIFY_STATUS, is_apply=False)
class SQLServerModifyInstStatusBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerModifyInstStatusSerializer
    alarm_transform_serializer = SQLServerDownForAutoFixSerializer
    inner_flow_builder = SQLServerModifyInstStatusParamBuilder
    inner_flow_name = _("SQLServer 修改故障实例状态")
    retry_type = FlowRetryType.MANUAL_RETRY
    default_need_itsm = False
    default_need_manual_confirm = False
