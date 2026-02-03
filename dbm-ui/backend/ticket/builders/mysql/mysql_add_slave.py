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
from backend.db_meta.models import StorageInstance
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer, fetch_cluster_ids
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlAddSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class AddSlaveInfoSerializer(serializers.Serializer):
        new_slave = serializers.ListField(help_text=_("新从库机器信息列表"), child=HostInfoSerializer(), required=False)
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)

    infos = serializers.ListField(help_text=_("添加从库信息"), child=AddSlaveInfoSerializer())
    backup_source = serializers.ChoiceField(
        help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), required=False
    )
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    source_type = serializers.ChoiceField(
        help_text=_("资源来源类型"), choices=SourceType.get_choices(), required=False, default=SourceType.RESOURCE_AUTO
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        super().validated_cluster_type(attrs, ClusterType.TenDBHA)

        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 校验集群与新增slave云区域是否相同
        super().validate_hosts_clusters_in_same_cloud_area(attrs, host_key=["new_slave"], cluster_key=["cluster_ids"])

        return attrs


class MysqlAddSlaveParamBuilder(builders.FlowParamBuilder):
    # 复用重建 slave 的场景
    controller = MySQLController.mysql_add_slave_remote_scene

    def format_ticket_data(self):
        self.ticket_data["add_slave_only"] = True

        if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
            return

        # 重新组织infos结构：将每个new_slave拆分成独立的info对象
        new_infos = []
        for info in self.ticket_data["infos"]:
            cluster_ids = info.get("cluster_ids", [])
            new_slaves = info.get("new_slave", [])

            for new_slave in new_slaves:
                new_info = {
                    "cluster_ids": cluster_ids.copy(),  # 复制cluster_ids避免引用问题
                    "new_slave_ip": new_slave["ip"],  # 单个IP字符串
                    "new_slave": new_slave,  # 保留完整的new_slave信息
                    "resource_spec": info.get("resource_spec", {}),
                }
                new_infos.append(new_info)

        # 替换原来的infos结构
        self.ticket_data["infos"] = new_infos


class MysqlAddSlaveResourceParamBuilder(BaseOperateResourceParamBuilder):
    @classmethod
    def patch_slave_subzone(cls, ticket_data):
        cluster_ids = fetch_cluster_ids(ticket_data)
        masters = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(cluster__in=cluster_ids, instance_inner_role=InstanceInnerRole.MASTER)
        )
        cluster_id__master_map = {master.cluster.first().id: master for master in masters}
        for info in ticket_data["infos"]:
            master = cluster_id__master_map[info["cluster_ids"][0]]
            cls.patch_common_affinity(
                info,
                role="new_slave",
                cluster=master.cluster.first(),
                exclusive_hosts=[master.machine],
            )

    def format(self):
        self.patch_slave_subzone(self.ticket_data)

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]

        # 重新组织infos结构：将每个new_slave拆分成独立的info对象
        new_infos = []
        for info in ticket_data["infos"]:
            cluster_ids = info.get("cluster_ids", [])
            new_slaves = info.get("new_slave", [])

            for new_slave in new_slaves:
                new_info = {
                    "cluster_ids": cluster_ids.copy(),  # 复制cluster_ids避免引用问题
                    "new_slave_ip": new_slave["ip"],  # 单个IP字符串
                    "new_slave": new_slave,  # 保留完整的new_slave信息
                    "resource_spec": info.get("resource_spec", {}),
                }
                new_infos.append(new_info)

        # 替换原来的infos结构
        ticket_data["infos"] = new_infos

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_ADD_SLAVE, is_apply=True)
class MysqlAddSlaveFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MysqlAddSlaveDetailSerializer
    inner_flow_builder = MysqlAddSlaveParamBuilder
    inner_flow_name = _("添加从库执行")
    resource_batch_apply_builder = MysqlAddSlaveResourceParamBuilder
