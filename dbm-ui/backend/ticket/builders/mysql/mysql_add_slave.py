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
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlAddSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class AddSlaveInfoSerializer(serializers.Serializer):
        new_slave = HostInfoSerializer(help_text=_("新从库机器信息"), required=False)
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        backup_source = serializers.ChoiceField(
            help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), required=False
        )
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)

    infos = serializers.ListField(help_text=_("添加从库信息"), child=AddSlaveInfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super().validate_cluster_can_access(attrs)
        super().validate_cluster_type(attrs, ClusterType.TenDBHA)

        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 校验集群与新增slave云区域是否相同
        super().validate_hosts_clusters_in_same_cloud_area(attrs, host_key=["new_slave"], cluster_key=["cluster_ids"])

        return attrs


class MysqlAddSlaveParamBuilder(builders.FlowParamBuilder):
    # 复用重建 slave 的场景
    controller = MySQLController.mysql_add_slave_scene

    def format_ticket_data(self):
        self.ticket_data["add_slave_only"] = True

        if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
            return

        for info in self.ticket_data["infos"]:
            info["new_slave_ip"] = info["new_slave"]["ip"]


class MysqlAddSlaveResourceParamBuilder(BaseOperateResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            info["new_slave"] = info.pop("new_slave")[0]
            info["new_slave_ip"] = info["new_slave"]["ip"]

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_ADD_SLAVE)
class MysqlAddSlaveFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlAddSlaveDetailSerializer
    inner_flow_builder = MysqlAddSlaveParamBuilder
    inner_flow_name = _("添加从库执行")
    resource_batch_apply_builder = MysqlAddSlaveResourceParamBuilder
