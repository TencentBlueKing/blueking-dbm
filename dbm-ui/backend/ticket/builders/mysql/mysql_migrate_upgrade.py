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

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.flow.consts import MySQLBackupTypeEnum
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    HostInfoSerializer,
    HostRecycleSerializer,
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

        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(), min_length=1)
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)
        pkg_id = serializers.IntegerField(help_text=_("目标版本包ID"))
        new_db_module_id = serializers.IntegerField(help_text=_("数据库模块ID"))
        new_master = HostInfoSerializer(help_text=_("新主库主机"), required=False)
        new_slave = HostInfoSerializer(help_text=_("新从库主机"), required=False)
        read_only_slaves = serializers.ListSerializer(
            help_text=_("只读从库（非 standby）"), child=ReadOnlySlaveSerializer(), required=False, allow_empty=True
        )

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    source_type = serializers.ChoiceField(
        help_text=_("资源来源类型"), choices=SourceType.get_choices(), required=False, default=SourceType.RESOURCE_AUTO
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    infos = serializers.ListField(help_text=_("添加信息"), child=InfoSerializer())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super(MysqlMigrateUpgradeDetailSerializer, self).validate_cluster_can_access(attrs)
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
        if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
            return
        for info in self.ticket_data["infos"]:
            info["ro_slaves"] = [
                {"old_ro_slave": slave["old_slave"], "new_ro_slave": slave["new_slave"]}
                for slave in info.pop("read_only_slaves", [])
            ]


class MysqlMigrateUpgradeResourceParamBuilder(BaseOperateResourceParamBuilder):
    def auto_patch_info(self, info, info_index, nodes, cluster):
        info["new_master"] = nodes[f"{info_index}_backend_group"][0]["master"]
        info["new_slave"] = nodes[f"{info_index}_backend_group"][0]["slave"]
        info["ro_slaves"] = [
            {
                "old_ro_slave": {
                    "bk_cloud_id": slave.machine.bk_cloud_id,
                    "bk_host_id": slave.machine.bk_host_id,
                    "ip": slave.machine.ip,
                },
                "new_ro_slave": nodes[f"{info_index}_{slave.machine.bk_host_id}"][0],
            }
            for slave in cluster.storageinstance_set.all()
            if slave.instance_role == InstanceRole.BACKEND_SLAVE and not slave.is_stand_by
        ]

    def manual_patch_info(self, info, info_index, cluster, nodes):
        info["new_master"] = info["new_master"][0]
        info["new_slave"] = info["new_slave"][0]
        info["ro_slaves"] = [
            {"old_ro_slave": slave["old_slave"], "new_ro_slave": slave["new_slave"]}
            for slave in info.pop("read_only_slaves", [])
        ]
        # 弹出read_only_new_slave，这个key仅作资源池申请
        if info.get("read_only_new_slave"):
            info.pop("read_only_new_slave")

    def post_callback(self):
        # 通过资源池获取到的节点
        nodes = self.ticket_data.pop("nodes", [])

        cluster_ids = list(itertools.chain(*[infos["cluster_ids"] for infos in self.ticket.details["infos"]]))
        id_cluster_map = Cluster.objects.prefetch_related(
            "storageinstance_set", "storageinstance_set__machine"
        ).in_bulk(cluster_ids, field_name="id")

        next_flow = self.ticket.next_flow()
        # 获取 bk_host_ids

        ticket_data = next_flow.details["ticket_data"]
        for info_index, info in enumerate(ticket_data["infos"]):
            # 兼容资源池手动输入和自动匹配的协议
            cluster = id_cluster_map[info["cluster_ids"][0]]
            # self.auto_patch_info(info, info_index, nodes, cluster)
            self.manual_patch_info(info, info_index, cluster, nodes)
            ticket_data["infos"][info_index] = info

        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(TicketType.MYSQL_MIGRATE_UPGRADE, is_apply=True, is_recycle=True)
class MysqlMigrateUpgradeFlowBuilder(MysqlMasterSlaveSwitchFlowBuilder):
    serializer = MysqlMigrateUpgradeDetailSerializer
    inner_flow_builder = MysqlMigrateUpgradeParamBuilder
    inner_flow_name = TicketType.get_choice_label(TicketType.MYSQL_MIGRATE_UPGRADE)
    resource_batch_apply_builder = MysqlMigrateUpgradeResourceParamBuilder
    need_patch_recycle_host_details = True

    def patch_auto_match_resource_spec(self, id_cluster_map):
        # 自动匹配补充规格信息
        resource_spec = {}
        for info in self.ticket.details["infos"]:
            # 主从规格
            cluster = id_cluster_map[info["cluster_ids"][0]]
            ins = cluster.storageinstance_set.first()
            resource_spec["backend_group"] = {
                "spec_id": ins.machine.spec_id,
                "count": 1,
                "location_spec": {"city": cluster.region, "sub_zone_ids": [ins.machine.bk_sub_zone_id]},
                "affinity": cluster.disaster_tolerance_level,
            }
            # 只读从库，按原规格替换
            for ins in cluster.storageinstance_set.all():
                if ins.instance_role == InstanceRole.BACKEND_SLAVE and not ins.is_stand_by:
                    resource_spec[ins.machine.bk_host_id] = {
                        "spec_id": ins.machine.spec_id,
                        "count": 1,
                        "location_spec": {"city": cluster.region, "sub_zone_ids": [ins.machine.bk_sub_zone_id]},
                        "affinity": AffinityEnum.NONE.value,
                    }
                    info["old_nodes"]["old_slave"].append(ins.machine.simple_desc)
            # 覆写resource_spec
            info["resource_spec"] = resource_spec

    def patch_manual_match_resource_spec(self, id_cluster_map):
        # 手动匹配补充规格信息
        for info in self.ticket.details["infos"]:
            read_only_new_slave = [slave["new_slave"] for slave in info["read_only_slaves"]]
            read_only_old_slave = [slave["old_slave"] for slave in info["read_only_slaves"]]
            info["old_nodes"]["old_slave"].extend(read_only_old_slave)
            if read_only_new_slave:
                info["resource_spec"]["read_only_new_slave"] = {"spec_id": 0, "hosts": read_only_new_slave}

    def patch_ticket_detail(self):
        """mysql_master -> backend_group"""
        # 主从构成 backend group
        # 只读从库（非 standby） 各自单独成组

        cluster_ids = list(itertools.chain(*[infos["cluster_ids"] for infos in self.ticket.details["infos"]]))
        id_cluster_map = Cluster.objects.prefetch_related(
            "storageinstance_set", "storageinstance_set__machine"
        ).in_bulk(cluster_ids, field_name="id")

        # 补充下架机器的信息
        MysqlMigrateClusterFlowBuilder.get_old_master_slave_host(self.ticket.details["infos"], id_cluster_map)
        # 补充自动匹配的资源池信息
        # self.patch_auto_match_resource_spec(id_cluster_map)
        # 兼容方案，先走资源池手动匹配协议
        self.patch_manual_match_resource_spec(id_cluster_map)
        # 补充通用单据信息
        super().patch_ticket_detail()
