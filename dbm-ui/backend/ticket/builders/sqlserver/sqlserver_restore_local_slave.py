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
from backend.ticket.builders.common.base import InstanceInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class SQLServerRestoreLocalSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class SlaveInfoSerializer(serializers.Serializer):
        slave = InstanceInfoSerializer(help_text=_("从库实例信息"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    infos = serializers.ListField(help_text=_("重建从库列表"), child=SlaveInfoSerializer())

    def validate(self, attrs):
        # 校验实例的角色为slave
        # super(MysqlRestoreLocalSlaveDetailSerializer, self).validate_instance_role(
        #     attrs, instance_key=["slave"], role=InstanceInnerRole.SLAVE
        # )
        super().validate(attrs)
        return attrs


class SQLServerRestoreLocalSlaveParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.slave_rebuild_in_local_scene

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["slave_host"] = info.pop("slave")
            info["port"] = info["slave_host"].pop("port")


@builders.BuilderFactory.register(TicketType.SQLSERVER_RESTORE_LOCAL_SLAVE)
class SQLServerRestoreLocalSlaveFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = SQLServerRestoreLocalSlaveDetailSerializer
    inner_flow_builder = SQLServerRestoreLocalSlaveParamBuilder
    inner_flow_name = _("SQLServer Slave原地重建执行")
