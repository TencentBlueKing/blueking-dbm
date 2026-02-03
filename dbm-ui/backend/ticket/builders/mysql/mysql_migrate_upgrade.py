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

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import MySQLBackupTypeEnum
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    HostInfoSerializer,
    ResourceSpecBaseSerializer,
    fetch_cluster_ids,
)
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer
from backend.ticket.builders.mysql.mysql_master_slave_switch import (
    MysqlMasterSlaveSwitchFlowBuilder,
    MysqlMasterSlaveSwitchParamBuilder,
)
from backend.ticket.builders.mysql.mysql_migrate_cluster import MysqlMigrateClusterFlowBuilder
from backend.ticket.constants import TicketType


class MysqlMigrateUpgradeDetailSerializer(MySQLBaseOperateDetailSerializer):
    class InfoSerializer(DisplayInfoSerializer):
        class ReadOnlySlaveSerializer(serializers.Serializer):
            old_slave = HostInfoSerializer(help_text=_("旧从库主机"))
            new_slave = HostInfoSerializer(help_text=_("新从库主机"))

        class ResourceModelSerializer(serializers.Serializer):
            backend_group = ResourceSpecBaseSerializer(help_text=_("主机规格信息"))
            new_read_slave = ResourceSpecBaseSerializer(help_text=_("只读从库主机规格信息"), required=False)

        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(), min_length=1)
        resource_spec = ResourceModelSerializer(help_text=_("资源规格参数"), required=False)
        pkg_id = serializers.IntegerField(help_text=_("目标版本包ID"))
        new_db_module_id = serializers.IntegerField(help_text=_("数据库模块ID"))
        read_only_slaves = serializers.ListSerializer(
            help_text=_("只读从库（非 standby）"), child=ReadOnlySlaveSerializer(), required=False, allow_empty=True
        )

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    infos = serializers.ListField(help_text=_("添加信息"), child=InfoSerializer())
    is_check_process = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    is_verify_checksum = serializers.BooleanField(help_text=_("是否检查主从数据校验结果"), default=True, required=False)
    need_checksum = serializers.BooleanField(help_text=_("执行前是否需要数据校验"), default=True, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        super(MysqlMigrateUpgradeDetailSerializer, self).validated_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验集群最近一次备份记录是逻辑备份
        cluster_ids = fetch_cluster_ids(attrs)
        super().validated_cluster_latest_backup(cluster_ids, attrs["backup_source"], MySQLBackupTypeEnum.LOGICAL)

        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        return attrs


class MysqlMigrateUpgradeParamBuilder(MysqlMasterSlaveSwitchParamBuilder):
    controller = MySQLController.tendbha_upgrade_scene

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["ro_slaves"] = [
                {"old_ro_slave": slave["old_slave"], "new_ro_slave": slave["new_slave"]}
                for slave in info.pop("read_only_slaves", [])
            ]


class MysqlMigrateUpgradeResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity("backend_group")

    def post_callback(self):
        # 通过资源池获取到的节点
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            backend_group = info.pop("backend_group")
            info["new_master"] = backend_group[0]["master"]
            info["new_slave"] = backend_group[0]["slave"]
        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(TicketType.MYSQL_MIGRATE_UPGRADE, is_apply=True, is_recycle=True)
class MysqlMigrateUpgradeFlowBuilder(MysqlMasterSlaveSwitchFlowBuilder):
    serializer = MysqlMigrateUpgradeDetailSerializer
    inner_flow_builder = MysqlMigrateUpgradeParamBuilder
    inner_flow_name = TicketType.get_choice_label(TicketType.MYSQL_MIGRATE_UPGRADE)
    resource_batch_apply_builder = MysqlMigrateUpgradeResourceParamBuilder
    need_patch_recycle_host_details = True
    validator = MySQLController.tendbha_upgrade_scene.validator

    def patch_auto_match_old_slave(self, id_cluster_map):
        for info in self.ticket.details["infos"]:
            cluster = id_cluster_map[info["cluster_ids"][0]]
            # 只读从库
            for ins in cluster.storageinstance_set.all():
                if ins.instance_role == InstanceRole.BACKEND_SLAVE and not ins.is_stand_by:
                    info["old_nodes"]["old_slave"].append(ins.machine.simple_desc)

    def patch_ticket_detail(self):
        """mysql_master -> backend_group"""
        cluster_ids = list(itertools.chain(*[infos["cluster_ids"] for infos in self.ticket.details["infos"]]))
        id_cluster_map = Cluster.objects.prefetch_related(
            "storageinstance_set", "storageinstance_set__machine"
        ).in_bulk(cluster_ids, field_name="id")

        # 补充下架机器的信息
        MysqlMigrateClusterFlowBuilder.get_old_master_slave_host(self.ticket.details["infos"], id_cluster_map)
        self.patch_auto_match_old_slave(id_cluster_map)
        # 补充通用单据信息
        super().patch_ticket_detail()
