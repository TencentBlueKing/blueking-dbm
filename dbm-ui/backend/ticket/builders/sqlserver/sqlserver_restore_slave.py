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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.builders.sqlserver.base import SQLServerBaseOperateResourceParamBuilder
from backend.ticket.constants import TicketType


class SQLServerRestoreSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class SlaveInfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群列表"), child=serializers.IntegerField())
        resource_spec = serializers.JSONField(help_text=_("资源池规格"), required=False)
        old_slave_host = HostInfoSerializer(help_text=_("旧slave机器信息"))
        new_slave_host = HostInfoSerializer(help_text=_("新slave机器信息"), required=False)

    infos = serializers.ListField(help_text=_("重建从库列表"), child=SlaveInfoSerializer())
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())

    def validate(self, attrs):
        # 校验实例的角色为slave
        # super(MysqlRestoreLocalSlaveDetailSerializer, self).validate_instance_role(
        #     attrs, instance_key=["slave"], role=InstanceInnerRole.SLAVE
        # )
        super().validate(attrs)
        return attrs


class SQLServerRestoreSlaveFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.slave_rebuild_in_new_slave_scene

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["slave_host"] = info.pop("slave")
            info["port"] = info["slave_host"].pop("port")


class SQLServerRestoreSlaveResourceParamBuilder(SQLServerBaseOperateResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            info["new_slave_host"] = info["sqlserver"][0]
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.SQLSERVER_RESTORE_SLAVE)
class SQLServerRestoreSlaveFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = SQLServerRestoreSlaveDetailSerializer
    resource_batch_apply_builder = SQLServerRestoreSlaveResourceParamBuilder
    inner_flow_builder = SQLServerRestoreSlaveFlowParamBuilder
    inner_flow_name = _("SQLServer Slave重建执行")
