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
import datetime
import itertools

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import MySQLBackupTypeEnum
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    HostInfoSerializer,
    fetch_cluster_ids,
)
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer
from backend.ticket.builders.mysql.mysql_master_slave_switch import (
    MysqlMasterSlaveSwitchFlowBuilder,
    MysqlMasterSlaveSwitchParamBuilder,
)
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
    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    infos = serializers.ListField(help_text=_("添加信息"), child=InfoSerializer())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super(MysqlMigrateUpgradeDetailSerializer, self).validate_cluster_can_access(attrs)
        super(MysqlMigrateUpgradeDetailSerializer, self).validated_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验集群最近一次备份记录是逻辑备份
        now = datetime.datetime.now(datetime.timezone.utc)
        cluster_ids = fetch_cluster_ids(attrs)
        for cluster in cluster_ids:
            handler = FixPointRollbackHandler(cluster_id=cluster)
            backup = handler.query_latest_backup_log(rollback_time=now, backup_source=attrs["backup_source"])
            if not backup or backup["backup_type"] != MySQLBackupTypeEnum.LOGICAL:
                raise serializers.ValidationError(_("集群{}无法找到最近一次备份，或最近一次备份不为逻辑备份").format(cluster))

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
            cluster = id_cluster_map[info["cluster_ids"][0]]
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
            ticket_data["infos"][info_index] = info

        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(TicketType.MYSQL_MIGRATE_UPGRADE, is_apply=True)
class MysqlMigrateUpgradeFlowBuilder(MysqlMasterSlaveSwitchFlowBuilder):
    serializer = MysqlMigrateUpgradeDetailSerializer
    inner_flow_builder = MysqlMigrateUpgradeParamBuilder
    inner_flow_name = TicketType.get_choice_label(TicketType.MYSQL_MIGRATE_UPGRADE)
    resource_batch_apply_builder = MysqlMigrateUpgradeResourceParamBuilder

    def patch_ticket_detail(self):
        """mysql_master -> backend_group"""
        # 主从构成 backend group
        # 只读从库（非 standby） 各自单独成组
        super().patch_ticket_detail()

        resource_spec = {}
        cluster_ids = list(itertools.chain(*[infos["cluster_ids"] for infos in self.ticket.details["infos"]]))

        id_cluster_map = Cluster.objects.prefetch_related(
            "storageinstance_set", "storageinstance_set__machine"
        ).in_bulk(cluster_ids, field_name="id")

        for info in self.ticket.details["infos"]:
            cluster = id_cluster_map[info["cluster_ids"][0]]
            # 主从规格
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
            info["resource_spec"] = resource_spec

        self.ticket.save(update_fields=["details"])
