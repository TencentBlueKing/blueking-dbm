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

from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate, HostInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.builders.sqlserver.base import SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class SQLServerMasterSlaveSwitchDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        master = HostInfoSerializer(help_text=_("主库 IP"))
        slave = HostInfoSerializer(help_text=_("从库 IP"))
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    force = serializers.BooleanField(help_text=_("是否强制切换(互切固定为false)"), default=False, required=False)

    def validate(self, attrs):
        # 校验集群是否可用
        # super().validate_cluster_can_access(attrs)

        # 校验slave实例的is_stand_by为True
        slave_insts = [f"{info['slave']['ip']}" for info in attrs["infos"]]
        CommonValidate.validate_slave_is_stand_by(slave_insts)

        return attrs


class SQLServerMasterSlaveSwitchParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.ha_switch_scene

    def format_ticket_data(self):
        self.ticket_data["force"] = False


@builders.BuilderFactory.register(TicketType.SQLSERVER_MASTER_SLAVE_SWITCH)
class SQLServerMasterSlaveSwitchFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = SQLServerMasterSlaveSwitchDetailSerializer
    inner_flow_builder = SQLServerMasterSlaveSwitchParamBuilder
    inner_flow_name = _("SQLServer 主从互换执行")
