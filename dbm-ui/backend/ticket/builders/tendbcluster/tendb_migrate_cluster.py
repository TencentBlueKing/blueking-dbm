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
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer, HostRecycleSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.mysql_migrate_cluster import (
    MysqlMigrateClusterParamBuilder,
    MysqlMigrateClusterResourceParamBuilder,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class TendbClusterMigrateClusterDetailSerializer(TendbBaseOperateDetailSerializer):
    class MigrateClusterInfoSerializer(serializers.Serializer):
        class OldMasterSlaveSerializer(serializers.Serializer):
            old_master = serializers.ListSerializer(child=HostInfoSerializer(help_text=_("旧主库主机"), required=False))
            old_slave = serializers.ListSerializer(child=HostInfoSerializer(help_text=_("旧从库主机"), required=False))

        new_master = HostInfoSerializer(help_text=_("新主库主机"), required=False)
        new_slave = HostInfoSerializer(help_text=_("新从库主机"), required=False)
        old_nodes = OldMasterSlaveSerializer(help_text=_("旧主从主机"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)
        cluster_id = serializers.IntegerField(help_text=_("集群ID列表"))

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    infos = serializers.ListSerializer(help_text=_("克隆主从信息"), child=MigrateClusterInfoSerializer())
    backup_source = serializers.ChoiceField(
        help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), default=MySQLBackupSource.REMOTE
    )
    is_safe = serializers.BooleanField(help_text=_("安全模式"), default=True)

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super().validate_cluster_can_access(attrs)
        # TODO: 校验old_master/old_slave是一对主从
        return attrs


class TendbClusterMigrateClusterParamBuilder(MysqlMigrateClusterParamBuilder):
    controller = SpiderController.tendb_cluster_remote_migrate

    def format_ticket_data(self):
        super().format_ticket_data()


class TendbClusterMigrateClusterResourceParamBuilder(MysqlMigrateClusterResourceParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_MIGRATE_CLUSTER, is_apply=True, is_recycle=True)
class TendbClusterMigrateClusterFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbClusterMigrateClusterDetailSerializer
    inner_flow_builder = TendbClusterMigrateClusterParamBuilder
    inner_flow_name = _("TenDB Cluster 主从迁移执行")
    resource_batch_apply_builder = TendbClusterMigrateClusterResourceParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY
    need_patch_recycle_host_details = True
