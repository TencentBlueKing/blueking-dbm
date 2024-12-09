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

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import StorageInstance
from backend.db_services.dbbase.constants import IpSource
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
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)

    def validate(self, attrs):
        cluster_ids = fetch_cluster_ids(attrs)

        # 校验集群是否可用，集群类型为高可用
        super(MysqlRestoreSlaveDetailSerializer, self).validate_cluster_can_access(attrs)
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
    @classmethod
    def patch_slave_subzone(cls, ticket_data):
        # TODO: 后续改造为，尽量与原slave一致，不一致再满足亲和性
        slave_host_ids = [s["bk_host_id"] for info in ticket_data["infos"] for s in info["old_nodes"]["old_slave"]]
        slaves = StorageInstance.objects.prefetch_related("as_receiver__ejector__machine", "machine").filter(
            machine__bk_host_id__in=slave_host_ids
        )
        slave_host_map = {slave.machine.bk_host_id: slave for slave in slaves}
        for info in ticket_data["infos"]:
            resource_spec = info["resource_spec"]["new_slave"]
            slave = slave_host_map[info["old_nodes"]["old_slave"][0]["bk_host_id"]]
            master_subzone_id = slave.as_receiver.get().ejector.machine.bk_sub_zone_id
            # 同城跨园区，要求slave和master在不同subzone
            if resource_spec["affinity"] == AffinityEnum.CROS_SUBZONE:
                resource_spec["location_spec"].update(sub_zone_ids=[master_subzone_id], include_or_exclue=False)
            # 同城同园区，要求slave和master在一个subzone
            elif resource_spec["affinity"] in [AffinityEnum.SAME_SUBZONE, AffinityEnum.SAME_SUBZONE_CROSS_SWTICH]:
                resource_spec["location_spec"].update(sub_zone_ids=[master_subzone_id], include_or_exclue=True)

    def format(self):
        # 补充亲和性和城市信息
        super().patch_info_affinity_location(roles=["new_slave"])
        # 补充slave园区申请
        self.patch_slave_subzone(self.ticket_data)

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
