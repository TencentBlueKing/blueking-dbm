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
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    HostInfoSerializer,
    HostRecycleSerializer,
    fetch_cluster_ids,
)
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlRestoreSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class RestoreInfoSerializer(serializers.Serializer):
        class OldSlaveSerializer(serializers.Serializer):
            old_slave = serializers.ListSerializer(child=HostInfoSerializer())

        old_nodes = OldSlaveSerializer(help_text=_("旧从库信息"))
        new_slave = HostInfoSerializer(help_text=_("新从库 IP"), required=False)
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    infos = serializers.ListField(help_text=_("集群重建信息"), child=RestoreInfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    source_type = serializers.ChoiceField(
        help_text=_("资源来源类型"), choices=SourceType.get_choices(), required=False, default=SourceType.RESOURCE_AUTO
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    disable_manual_confirm = serializers.BooleanField(help_text=(_("自愈单据禁用人工确认")), default=False)

    def validate(self, attrs):
        cluster_ids = fetch_cluster_ids(attrs)
        attrs = super().validate(attrs)

        super(MysqlRestoreSlaveDetailSerializer, self).validated_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验old_slave的实例角色为slave
        super(MysqlRestoreSlaveDetailSerializer, self).validate_instance_role(
            attrs, instance_key=["old_slave"], role=InstanceInnerRole.SLAVE
        )

        # 校验old_slave的关联集群是否一致
        super(MysqlRestoreSlaveDetailSerializer, self).validate_instance_related_clusters(
            attrs, instance_key=["old_slave"], cluster_key=["cluster_ids"], role=InstanceInnerRole.SLAVE
        )

        # 校验集群存在最近一次全备
        super(MysqlRestoreSlaveDetailSerializer, self).validated_cluster_latest_backup(
            cluster_ids, attrs["backup_source"]
        )

        return attrs


class MysqlRestoreSlaveParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_restore_slave_remote_scene

    def format_ticket_data(self):
        self.ticket_data["add_slave_only"] = False
        for info in self.ticket_data["infos"]:
            old_slave = info["old_nodes"]["old_slave"][0]
            info["old_slave_ip"], info["bk_old_slave"] = old_slave["ip"], old_slave

        if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
            return

        for info in self.ticket_data["infos"]:
            new_slave = info.pop("new_slave")
            info["new_slave_ip"], info["bk_new_slave"] = new_slave["ip"], new_slave


class MysqlRestoreSlaveResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity("new_slave", remain_machine_type="master", replace_key="old_slave")

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            info["bk_old_slave"], info["bk_new_slave"] = (
                info.pop("old_nodes")["old_slave"][0],
                info.pop("new_slave")[0],
            )
            info["old_slave_ip"], info["new_slave_ip"] = info["bk_old_slave"]["ip"], info["bk_new_slave"]["ip"]

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_RESTORE_SLAVE, is_apply=True, is_recycle=True)
class MysqlRestoreSlaveFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MysqlRestoreSlaveDetailSerializer
    inner_flow_builder = MysqlRestoreSlaveParamBuilder
    resource_batch_apply_builder = MysqlRestoreSlaveResourceParamBuilder
    need_patch_recycle_host_details = True
