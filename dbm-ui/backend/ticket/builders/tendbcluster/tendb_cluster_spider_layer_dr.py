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
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.db_meta.enums import MachineType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    HostInfoSerializer,
    TicketBaseValidateSerializerMixin,
)
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder
from backend.ticket.constants import TicketType


class TendbClusterSpiderLayerDrDetailSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    class SpiderDrInfoSerializer(serializers.Serializer):
        class OldProxySerializer(serializers.Serializer):
            proxy = serializers.ListSerializer(child=HostInfoSerializer())

        cluster_id = serializers.IntegerField(help_text=_("集群 ID"), required=True)
        spider_master_new_ip_list = serializers.ListField(
            help_text=_("新 Spider Master IP 列表"), child=HostInfoSerializer(), required=False
        )
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        old_nodes = OldProxySerializer(help_text=_("旧 Spider Master IP 列表"))
        strip_dns_before_install = serializers.BooleanField(help_text=_("安装前是否摘除 DNS"), default=True)

    infos = serializers.ListField(help_text=_("Spider 容灾切换/替换列表"), child=SpiderDrInfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL.value
    )


class TendbClusterSpiderLayerDrParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.placeholder


class TendbClusterSpiderLayerDrResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="spider_master_new_ip_list", remain_machine_type=MachineType.PROXY, replace_key="proxy", tolerance=0.5
        )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        infos = next_flow.details.get("ticket_data", {}).get("infos", [])
        for info in infos:
            if "old_nodes" in info:
                old_nodes_dict = info.pop("old_nodes")
                info["spider_master_old_ip_list"] = old_nodes_dict.get("proxy", [])

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_LAYER_DR)
class TendbClusterSpiderLayerDrFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = TendbClusterSpiderLayerDrDetailSerializer
    inner_flow_builder = TendbClusterSpiderLayerDrParamBuilder
    inner_flow_name = _("Tendb Cluster Spider故障重建执行")
    resource_batch_apply_builder = TendbClusterSpiderLayerDrResourceParamBuilder
    validator = None
