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

import operator
from functools import reduce

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import StorageInstance
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import InstanceInfoSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.builders.tendbcluster.base import TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbClusterRestoreLocalSlaveDetailSerializer(TendbBaseOperateDetailSerializer):
    class SlaveInfoSerializer(serializers.Serializer):
        slave = InstanceInfoSerializer(help_text=_("从库实例信息"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    infos = serializers.ListField(help_text=_("重建从库列表"), child=SlaveInfoSerializer())
    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)

    def validate(self, attrs):
        # 校验集群是否可用
        super(TendbBaseOperateDetailSerializer, self).validate_cluster_can_access(attrs)
        # TODO 校验slave角色信息
        return attrs


class TendbClusterRestoreLocalSlaveParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendb_cluster_remote_local_recover

    def format_ticket_data(self):
        # 查询重建的slave实例
        slave_filters = reduce(
            operator.or_,
            [Q(machine__ip=info["slave"]["ip"], port=info["slave"]["port"]) for info in self.ticket_data["infos"]],
        )
        # 查询实例对应的分片ID
        slaves = StorageInstance.objects.prefetch_related(
            "machine", "cluster", "as_receiver__tendbclusterstorageset"
        ).filter(slave_filters)
        # 按照ip聚合，补充slave重建信息
        ip__restore_infos: dict = {}
        for slave in slaves:
            shard_id = slave.as_receiver.first().tendbclusterstorageset.shard_id
            machine = slave.machine
            if slave.machine.ip not in ip__restore_infos:
                ip__restore_infos[slave.machine.ip] = {
                    "cluster_id": slave.cluster.first().id,
                    "shard_ids": [shard_id],
                    "slave_ip": machine.ip,
                    "bk_slave": {
                        "bk_biz_id": slave.bk_biz_id,
                        "bk_host_id": machine.bk_host_id,
                        "bk_cloud_id": machine.bk_cloud_id,
                        "ip": machine.ip,
                    },
                }
            else:
                ip__restore_infos[slave.machine.ip]["shard_ids"].append(shard_id)
        self.ticket_data["infos"] = list(ip__restore_infos.values())


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_RESTORE_LOCAL_SLAVE)
class TendbClusterRestoreLocalSlaveFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = TendbClusterRestoreLocalSlaveDetailSerializer
    inner_flow_builder = TendbClusterRestoreLocalSlaveParamBuilder
    inner_flow_name = _("TenDB Cluster Slave原地重建执行")
