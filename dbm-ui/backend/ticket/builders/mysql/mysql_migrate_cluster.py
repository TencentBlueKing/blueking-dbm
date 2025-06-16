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
import itertools

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    HostInfoSerializer,
    HostRecycleSerializer,
    fetch_cluster_ids,
)
from backend.ticket.builders.common.constants import MySQLBackupSource, OperaObjType
from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer
from backend.ticket.builders.mysql.mysql_master_slave_switch import (
    MysqlMasterSlaveSwitchFlowBuilder,
    MysqlMasterSlaveSwitchParamBuilder,
)
from backend.ticket.constants import TicketType


class MysqlMigrateClusterDetailSerializer(MySQLBaseOperateDetailSerializer):
    class MigrateClusterInfoSerializer(serializers.Serializer):
        new_master = HostInfoSerializer(help_text=_("新主库主机"), required=False)
        new_slave = HostInfoSerializer(help_text=_("新从库主机"), required=False)
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    infos = serializers.ListField(help_text=_("迁移主从信息"), child=MigrateClusterInfoSerializer())
    backup_source = serializers.ChoiceField(
        help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), default=MySQLBackupSource.REMOTE
    )
    is_safe = serializers.BooleanField(help_text=_("安全模式"), default=True)
    need_checksum = serializers.BooleanField(help_text=_("执行前是否需要数据校验"), default=True)
    opera_object = serializers.ChoiceField(help_text=_("操作对象类型"), choices=OperaObjType.get_choices(), required=False)

    def validate(self, attrs):
        cluster_ids = fetch_cluster_ids(attrs)

        # 校验集群是否可用，集群类型为高可用
        super().validate_cluster_can_access(attrs)
        super().validated_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验集群存在最近一次全备
        super().validated_cluster_latest_backup(cluster_ids, attrs["backup_source"])

        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 校验集群与新增master和slave云区域是否相同
        super().validate_hosts_clusters_in_same_cloud_area(
            attrs, host_key=["new_master", "new_slave"], cluster_key=["cluster_ids"]
        )

        return attrs


class MysqlMigrateClusterParamBuilder(MysqlMasterSlaveSwitchParamBuilder):
    controller = MySQLController.mysql_migrate_remote_scene

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["old_master_ip"] = info["old_nodes"]["old_master"][0]["ip"]
            info["old_slave_ip"] = info["old_nodes"]["old_slave"][0]["ip"]

        if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
            return

        for info in self.ticket_data["infos"]:
            info["new_master_ip"], info["new_slave_ip"] = info["new_master"]["ip"], info["new_slave"]["ip"]
            info["bk_new_master"], info["bk_new_slave"] = info.pop("new_master"), info.pop("new_slave")


class MysqlMigrateClusterResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_affinity_location()

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            # 兼容资源池手动选择和自动匹配的协议
            if "backend_group" in info:
                backend = info.pop("backend_group")[0]
                info["bk_new_master"], info["bk_new_slave"] = backend["master"], backend["slave"]
                # 修改规格key值
                info["resource_spec"]["remote"] = info["resource_spec"].pop("master")
                info["resource_spec"].pop("slave")
            else:
                info["bk_new_master"], info["bk_new_slave"] = info.pop("new_master")[0], info.pop("new_slave")[0]
            info["new_master_ip"], info["new_slave_ip"] = info["bk_new_master"]["ip"], info["bk_new_slave"]["ip"]
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_MIGRATE_CLUSTER, is_apply=True, is_recycle=True)
class MysqlMigrateClusterFlowBuilder(MysqlMasterSlaveSwitchFlowBuilder):
    serializer = MysqlMigrateClusterDetailSerializer
    inner_flow_builder = MysqlMigrateClusterParamBuilder
    inner_flow_name = TicketType.get_choice_label(TicketType.MYSQL_MIGRATE_CLUSTER)
    resource_batch_apply_builder = MysqlMigrateClusterResourceParamBuilder
    need_patch_recycle_host_details = True
    need_patch_machine_details = True

    @staticmethod
    def get_old_master_slave_host(infos, cluster_map):
        for info in infos:
            # 同机关联情况下，任取一台集群
            insts = cluster_map[info["cluster_ids"][0]].storageinstance_set.all()
            master = next(i for i in insts if i.instance_inner_role == InstanceInnerRole.MASTER)
            slave = next(i for i in insts if i.instance_inner_role == InstanceInnerRole.SLAVE and i.is_stand_by)
            # 补充下架的机器信息
            info["old_nodes"] = {"old_master": [master.machine.simple_desc], "old_slave": [slave.machine.simple_desc]}

    def patch_ticket_detail(self):
        cluster_ids = list(itertools.chain(*[infos["cluster_ids"] for infos in self.ticket.details["infos"]]))
        cluster_map = Cluster.objects.prefetch_related("storageinstance_set").in_bulk(cluster_ids, field_name="id")
        # mysql主从迁移会下架掉master和slave(stand by)
        self.get_old_master_slave_host(self.ticket.details["infos"], cluster_map)
        super().patch_ticket_detail()
