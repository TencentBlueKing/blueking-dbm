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
from backend.ticket.builders.common.base import InstanceInfoSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MysqlRestoreLocalSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class SlaveInfoSerializer(serializers.Serializer):
        slave = InstanceInfoSerializer(help_text=_("从库实例信息"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        backup_source = serializers.ChoiceField(
            help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), required=False
        )

    infos = serializers.ListField(help_text=_("重建从库列表"), child=SlaveInfoSerializer())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super(MysqlRestoreLocalSlaveDetailSerializer, self).validate_cluster_can_access(attrs)
        super(MysqlRestoreLocalSlaveDetailSerializer, self).validate_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验实例的角色为slave
        super(MysqlRestoreLocalSlaveDetailSerializer, self).validate_instance_role(
            attrs, instance_key=["slave"], role=InstanceInnerRole.SLAVE
        )

        # 校验实例属于当前集群
        super(MysqlRestoreLocalSlaveDetailSerializer, self).validate_instance_related_clusters(
            attrs, instance_key=["slave"], cluster_key=["cluster_id"], role=InstanceInnerRole.SLAVE
        )

        return attrs


class MysqlRestoreLocalSlaveParamBuilder(builders.FlowParamBuilder):
    controller_remote = MySQLController.mysql_restore_local_remote_scene
    controller_local = MySQLController.mysql_restore_local_slave_scene

    def build_controller_info(self) -> dict:
        backup_source = self.ticket_data.get("backup_source", MySQLBackupSource.LOCAL)
        self.controller = getattr(self, f"controller_{backup_source}")
        return super().build_controller_info()

    def format_ticket_data(self):
        for index, info in enumerate(self.ticket_data["infos"]):
            slave_ip, slave_port = info["slave"]["ip"], info["slave"]["port"]
            self.ticket_data["infos"][index].update({"slave_ip": slave_ip, "slave_port": int(slave_port)})


@builders.BuilderFactory.register(TicketType.MYSQL_RESTORE_LOCAL_SLAVE)
class MysqlSingleDestroyFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlRestoreLocalSlaveDetailSerializer
    inner_flow_builder = MysqlRestoreLocalSlaveParamBuilder
    inner_flow_name = _("Slave原地重建执行")
