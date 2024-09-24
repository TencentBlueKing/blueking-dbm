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
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.mysql.mysql_add_slave import MysqlAddSlaveResourceParamBuilder
from backend.ticket.builders.sqlserver.base import (
    BaseSQLServerHATicketFlowBuilder,
    SQLServerBaseOperateDetailSerializer,
    SQLServerBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class SQLServerAddSlaveDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class SlaveInfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群列表"), child=serializers.IntegerField())
        resource_spec = serializers.JSONField(help_text=_("资源池规格"), required=False)
        new_slave_host = HostInfoSerializer(help_text=_("新slave机器信息"), required=False)

    infos = serializers.ListField(help_text=_("重建从库列表"), child=SlaveInfoSerializer())
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super().validate_cluster_can_access(attrs)
        super().validated_cluster_type(attrs, ClusterType.SqlserverHA)

        super().validate(attrs)
        return attrs


class SQLServerAddSlaveFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.add_slave_scene

    def format_ticket_data(self):
        pass


class SQLServerAddSlaveResourceParamBuilder(SQLServerBaseOperateResourceParamBuilder):
    def format(self):
        # 补充城市和亲和性
        super().patch_info_affinity_location()
        # 新增slave亲和性同mysql一致
        MysqlAddSlaveResourceParamBuilder.patch_slave_subzone(self.ticket_data)

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            info["new_slave_host"] = info.pop("new_slave")[0]
            info["resource_spec"]["sqlserver_ha"] = info["resource_spec"].pop("new_slave")
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.SQLSERVER_ADD_SLAVE)
class SQLServerAddSlaveFlowBuilder(BaseSQLServerHATicketFlowBuilder):
    serializer = SQLServerAddSlaveDetailSerializer
    resource_batch_apply_builder = SQLServerAddSlaveResourceParamBuilder
    inner_flow_builder = SQLServerAddSlaveFlowParamBuilder
    inner_flow_name = _("SQLServer 添加Slave执行")
