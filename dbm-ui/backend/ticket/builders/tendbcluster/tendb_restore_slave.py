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
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.builders.mysql.mysql_restore_slave import MysqlRestoreSlaveDetailSerializer
from backend.ticket.constants import TicketType


class TendbClusterRestoreSlaveDetailSerializer(MysqlRestoreSlaveDetailSerializer):
    class RestoreInfoSerializer(serializers.Serializer):
        old_slave = HostInfoSerializer(help_text=_("旧从库 IP"))
        new_slave = HostInfoSerializer(help_text=_("新从库 IP"), required=False)
        resource_spec = serializers.JSONField(help_text=_("新从库资源池参数"), required=False)
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    infos = serializers.ListField(help_text=_("集群重建信息"), child=RestoreInfoSerializer())

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为tendbcluster
        super(MysqlRestoreSlaveDetailSerializer, self).validate_cluster_can_access(attrs)
        super(MysqlRestoreSlaveDetailSerializer, self).validate_cluster_type(attrs, ClusterType.TenDBCluster)
        # 校验新机器的云区域与集群一致
        if attrs["ip_source"] == IpSource.MANUAL_INPUT:
            super(MysqlRestoreSlaveDetailSerializer, self).validate_hosts_clusters_in_same_cloud_area(
                attrs, host_key=["new_slave"], cluster_key=["cluster_id"]
            )
        return attrs


class TendbClusterRestoreSlaveParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendb_cluster_remote_slave_recover

    def format_ticket_data(self):
        if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
            return

        for info in self.ticket_data["infos"]:
            info["old_slave_ip"], info["new_slave_ip"] = info["old_slave"]["ip"], info["new_slave"]["ip"]
            info["bk_old_slave"], info["bk_new_slave"] = info.pop("old_slave"), info.pop("new_slave")


class TendbClusterRestoreSlaveResourceParamBuilder(BaseOperateResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            info["bk_old_slave"], info["bk_new_slave"] = info.pop("old_slave"), info.pop("new_slave")[0]
            info["old_slave_ip"], info["new_slave_ip"] = info["bk_old_slave"]["ip"], info["bk_new_slave"]["ip"]

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_RESTORE_SLAVE, is_apply=True)
class TendbClusterRestoreSlaveFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = TendbClusterRestoreSlaveDetailSerializer
    inner_flow_builder = TendbClusterRestoreSlaveParamBuilder
    inner_flow_name = _("TenDB Cluster Slave重建")
    resource_apply_builder = TendbClusterRestoreSlaveResourceParamBuilder
