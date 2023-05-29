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

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer, InstanceInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MysqlRestoreSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class RestoreInfoSerializer(serializers.Serializer):
        old_slave = InstanceInfoSerializer(help_text=_("旧从库 IP"))
        new_slave = HostInfoSerializer(help_text=_("新从库 IP"))
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        backup_source = serializers.CharField(help_text=_("备份源"), required=False)

    infos = serializers.ListField(help_text=_("集群重建信息"), child=RestoreInfoSerializer())

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super(MysqlRestoreSlaveDetailSerializer, self).validate_cluster_can_access(attrs)
        super(MysqlRestoreSlaveDetailSerializer, self).validate_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验old_slave的实例角色为slave
        super(MysqlRestoreSlaveDetailSerializer, self).validate_instance_role(
            attrs, instance_key=["old_slave"], role=InstanceInnerRole.SLAVE
        )

        # 校验old_slave的关联集群是否一致
        super(MysqlRestoreSlaveDetailSerializer, self).validate_instance_related_clusters(
            attrs, instance_key=["old_slave"], cluster_key=["cluster_ids"], role=InstanceInnerRole.SLAVE
        )

        # 校验新机器的云区域与集群一致
        super(MysqlRestoreSlaveDetailSerializer, self).validate_hosts_clusters_in_same_cloud_area(
            attrs, host_key=["new_slave"], cluster_key=["cluster_ids"]
        )

        return attrs


class MysqlRestoreSlaveParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_restore_slave_scene

    def format_ticket_data(self):
        self.ticket_data["add_slave_only"] = False
        for info in self.ticket_data["infos"]:
            info["old_slave_ip"], info["new_slave_ip"] = info["old_slave"]["ip"], info["new_slave"]["ip"]


@builders.BuilderFactory.register(TicketType.MYSQL_RESTORE_SLAVE)
class MysqlSingleDestroyFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlRestoreSlaveDetailSerializer
    inner_flow_builder = MysqlRestoreSlaveParamBuilder
    inner_flow_name = _("Slave重建执行")
