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

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import StorageInstance
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.flow.engine.controller.oracle import OracleController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer, fetch_cluster_ids
from backend.ticket.builders.oracle.base import BaseOracleTicketFlowBuilder, OracleOpsBaseDetailSerializer
from backend.ticket.constants import TicketType


class OracleAddSlaveDetailSerializer(OracleOpsBaseDetailSerializer):
    class AddSlaveInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        old_node = HostInfoSerializer(help_text=_("旧机器信息"))
        old_master = HostInfoSerializer(help_text=_("旧master主机"), required=False)
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)

    infos = serializers.ListField(help_text=_("添加从库信息"), child=AddSlaveInfoSerializer())
    db_version = serializers.CharField(help_text=_("数据库版本"), required=False)
    patch_list = serializers.ListField(
        help_text=_("补丁列表"), child=serializers.CharField(), required=False, default=["Opatch6880880", "p28204707"]
    )
    flow_type = serializers.CharField(help_text=_("集群版本"))
    upstream_type = serializers.CharField(help_text=_("前端展示字段"), required=False)
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.RESOURCE_POOL
    )
    source_type = serializers.ChoiceField(
        help_text=_("资源来源类型"), choices=SourceType.get_choices(), required=False, default=SourceType.RESOURCE_AUTO
    )


class OracleAddSlaveParamBuilder(builders.FlowParamBuilder):
    # 复用重建 slave 的场景
    controller = OracleController.oracle_add_slave_scene


class OracleAddSlaveResourceParamBuilder(BaseOperateResourceParamBuilder):
    @classmethod
    def patch_slave_subzone(cls, ticket_data):
        cluster_ids = fetch_cluster_ids(ticket_data)
        masters = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(cluster__in=cluster_ids, instance_inner_role=InstanceInnerRole.PRIMARY)
        )
        cluster_id__master_map = {master.cluster.first().id: master for master in masters}
        for info in ticket_data["infos"]:
            master = cluster_id__master_map[info["cluster_ids"][0]]
            if info["old_node"]["ip"] == master.machine.ip:
                cls.patch_common_affinity(info, role="oracle", cluster=master.cluster.first(), no_need_affinity=True)
            else:
                cls.patch_common_affinity(
                    info, role="oracle", cluster=master.cluster.first(), exclusive_hosts=[master.machine]
                )

    def format(self):
        self.patch_slave_subzone(self.ticket_data)

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            new_slave = info.pop("oracle")
            info["new_slave"] = new_slave[0]

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.ORACLE_ADD_SLAVE, is_apply=True, iam=ActionEnum.ORACLE_MANAGE)
class OracleAddSlaveFlowBuilder(BaseOracleTicketFlowBuilder):
    serializer = OracleAddSlaveDetailSerializer
    inner_flow_builder = OracleAddSlaveParamBuilder
    inner_flow_name = _("ORACLE 添加从库")
    resource_batch_apply_builder = OracleAddSlaveResourceParamBuilder


@builders.BuilderFactory.register(TicketType.ORACLE_REPLACE_HOST, is_apply=True, iam=ActionEnum.ORACLE_MANAGE)
class OracleReplaceHostFlowBuilder(BaseOracleTicketFlowBuilder):
    serializer = OracleAddSlaveDetailSerializer
    inner_flow_builder = OracleAddSlaveParamBuilder
    inner_flow_name = _("ORACLE 整机替换")
    resource_batch_apply_builder = OracleAddSlaveResourceParamBuilder
