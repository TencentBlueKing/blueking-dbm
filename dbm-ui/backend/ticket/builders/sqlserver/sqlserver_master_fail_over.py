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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder
from backend.ticket.builders.sqlserver.sqlserver_master_slave_switch import SQLServerMasterSlaveSwitchDetailSerializer
from backend.ticket.constants import TicketType


class SQLServerMasterFailOverDetailSerializer(SQLServerMasterSlaveSwitchDetailSerializer):
    force = serializers.BooleanField(help_text=_("是否强制切换(强切固定为true)"), default=True, required=False)

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super().validate_cluster_can_access(attrs)
        super().validated_cluster_type(attrs, ClusterType.SqlserverHA)
        return attrs


class SQLServerMasterFailOverParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.ha_fail_over_scene

    def format_ticket_data(self):
        self.ticket_data["force"] = True


@builders.BuilderFactory.register(TicketType.SQLSERVER_MASTER_FAIL_OVER)
class SQLServerMasterSlaveSwitchFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerMasterFailOverDetailSerializer
    inner_flow_builder = SQLServerMasterFailOverParamBuilder
    inner_flow_name = _("SQLServer 主故障切换执行")
