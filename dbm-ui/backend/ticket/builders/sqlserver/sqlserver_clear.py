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

from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class SQLServerClearDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class ClearDataInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        clean_dbs = serializers.ListField(help_text=_("清档db列表"), child=serializers.CharField())
        clean_tables = serializers.ListField(help_text=_("清档表"), child=serializers.CharField())
        ignore_clean_tables = serializers.ListField(help_text=_("忽略表"), required=False, default=[])

    is_safe = serializers.BooleanField(help_text=_("安全模式"), required=False, default=True)
    infos = serializers.ListSerializer(help_text=_("清档信息列表"), child=ClearDataInfoSerializer())

    def validate(self, attrs):
        """验证库表数据库的数据"""
        super().validate(attrs)
        return attrs


class SQLServerClearFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.clean_dbs_scene


@builders.BuilderFactory.register(TicketType.SQLSERVER_CLEAR_DBS)
class SQLServerClearFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerClearDetailSerializer
    inner_flow_builder = SQLServerClearFlowParamBuilder
    inner_flow_name = _("SQLServer 清档执行")
    retry_type = FlowRetryType.MANUAL_RETRY
