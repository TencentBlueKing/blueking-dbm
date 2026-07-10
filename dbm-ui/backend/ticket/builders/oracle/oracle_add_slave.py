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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.oracle import OracleController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer
from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer
from backend.ticket.builders.oracle.base import BaseOracleTicketFlowBuilder
from backend.ticket.constants import TicketType


class OracleAddSlaveDetailSerializer(MySQLBaseOperateDetailSerializer):
    class RestoreInfoSerializer(serializers.Serializer):
        old_node = HostInfoSerializer(help_text=_("旧实例信息"), required=False)
        new_slave = HostInfoSerializer(help_text=_("新从库信息"), required=False)
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
        replace_flag = serializers.BooleanField(help_text=_("是否替换"), required=False)

    infos = serializers.ListField(help_text=_("集群添加从库/重建从库"), child=RestoreInfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    db_version = serializers.CharField(help_text=_("数据库版本"), required=False)
    patch_list = serializers.ListField(help_text=_("补丁列表"), child=serializers.CharField(), required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # 资源池模式下 new_slave 由资源申请后回填，此处不做手动 IP 强校验
        if attrs.get("ip_source") == IpSource.RESOURCE_POOL:
            return attrs
        return attrs


class OracleAddSlaveParamBuilder(builders.FlowParamBuilder):
    controller = OracleController.oracle_add_slave_scene


class OracleAddSlaveResourceParamBuilder(BaseOperateResourceParamBuilder):
    """
    Oracle 添加备库场景的资源池申请参数构造器。
    - format: 基类补 bk_cloud_id/bk_biz_id, 资源池角色 key 使用 "oracle"。
    - post_callback: 将资源池返回的 info["oracle"] 转成 info["new_slave"] 字典结构,
      保持后续 flow 中 info["new_slave"]["ip"] 的用法不变。
    """

    def format(self):
        super().format()

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data.get("infos", []):
            # 资源池返回的角色分组名与 resource_spec 的 key 一致, 这里是 "oracle"
            applied_hosts = info.pop("oracle", None)
            if not applied_hosts:
                continue
            new_host = applied_hosts[0]
            # 新备库端口与旧实例端口保持一致(同集群约定)
            info["new_slave"] = {
                "ip": new_host["ip"],
                "bk_cloud_id": new_host["bk_cloud_id"],
                "bk_host_id": new_host.get("bk_host_id"),
                "bk_biz_id": new_host.get("bk_biz_id"),
            }

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.ORACLE_ADD_SLAVE, is_apply=True)
class OracleAddSlaveFlowBuilder(BaseOracleTicketFlowBuilder):
    serializer = OracleAddSlaveDetailSerializer
    inner_flow_builder = OracleAddSlaveParamBuilder
    resource_batch_apply_builder = OracleAddSlaveResourceParamBuilder
