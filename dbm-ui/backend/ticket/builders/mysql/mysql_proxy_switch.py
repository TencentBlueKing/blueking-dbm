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

from backend.db_meta.enums import MachineType
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    HostRecycleSerializer,
    InstanceInfoSerializer,
)
from backend.ticket.builders.common.constants import OperaObjType
from backend.ticket.builders.mysql.base import (
    BaseMySQLHATicketFlowBuilder,
    MySQLBaseOperateDetailSerializer,
    MySQLBasePauseParamBuilder,
)
from backend.ticket.constants import FlowRetryType, TicketType


class MysqlProxySwitchDetailSerializer(MySQLBaseOperateDetailSerializer):
    class SwitchInfoSerializer(DisplayInfoSerializer):
        class OldProxySerializer(serializers.Serializer):
            origin_proxy = serializers.ListSerializer(child=InstanceInfoSerializer())

        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        old_nodes = OldProxySerializer(help_text=_("旧Proxy实例信息"))
        target_proxy_pkg_id = serializers.IntegerField(help_text=_("新机器部署的介质包ID，在FLow计算赋值"), required=False, default=0)
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        related_instances = serializers.ListSerializer(
            help_text=_("关联的实例"), child=serializers.JSONField(), required=False
        )
        origin_proxy_ip = serializers.JSONField(help_text=_("原始proxy信息"))

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.RESOURCE_POOL
    )
    source_type = serializers.ChoiceField(
        help_text=_("资源来源类型"), choices=SourceType.get_choices(), required=False, default=SourceType.RESOURCE_AUTO
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    is_safe = serializers.BooleanField(help_text=_("是否安全模式"), required=False, default=True)
    infos = serializers.ListField(help_text=_("替换信息"), child=SwitchInfoSerializer())
    opera_object = serializers.ChoiceField(help_text=_("操作对象类型"), choices=OperaObjType.get_choices(), required=False)
    disable_manual_confirm = serializers.BooleanField(help_text=(_("自愈单据禁用人工确认")), default=False)


class MysqlProxySwitchParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_switch_scene
    validator = MySQLController.mysql_proxy_switch_scene.validator

    @classmethod
    def merge_same_proxy_clusters(cls, infos):
        """聚合替换相同的proxy的集群"""
        switch_proxy_cluster_map = {}
        for info in infos:
            switch_key = f"{info['origin_proxy_ip']['bk_host_id']}--{info['target_proxy_ip']['bk_host_id']}"
            if switch_key not in switch_proxy_cluster_map:
                switch_proxy_cluster_map[switch_key] = {**info, "cluster_ids": []}
            switch_proxy_cluster_map[switch_key]["cluster_ids"].extend(info["cluster_ids"])
        return list(switch_proxy_cluster_map.values())


class MysqlProxySwitchResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="target_proxy", remain_machine_type=MachineType.PROXY, replace_key="origin_proxy", tolerance=0.5
        )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            info["target_proxy"] = info.pop("target_proxy")[0]
            info["target_proxy_ip"] = info["target_proxy"]
        # 聚合集群
        infos = MysqlProxySwitchParamBuilder.merge_same_proxy_clusters(ticket_data["infos"])
        next_flow.details["ticket_data"]["infos"] = infos
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_SWITCH, is_apply=True, is_recycle=True)
class MysqlProxySwitchFlowBuilder(BaseMySQLHATicketFlowBuilder):
    need_patch_recycle_host_details = True
    need_patch_machine_details = True
    retry_type = FlowRetryType.MANUAL_RETRY
    serializer = MysqlProxySwitchDetailSerializer
    inner_flow_builder = MysqlProxySwitchParamBuilder
    resource_batch_apply_builder = MysqlProxySwitchResourceParamBuilder
    pause_node_builder = MySQLBasePauseParamBuilder
