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
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, DisplayInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MysqlProxyConfChangeDetailSerializer(MySQLBaseOperateDetailSerializer):
    class ProxyConfChangeInfoSerializer(DisplayInfoSerializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        origin_proxy_ips = serializers.ListField(help_text=_("资源规格"), child=serializers.JSONField())
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.RESOURCE_POOL
    )
    is_safe = serializers.BooleanField(help_text=_("是否安全模式"), required=False, default=True)
    infos = serializers.ListField(help_text=_("替换信息"), child=ProxyConfChangeInfoSerializer())


class MysqlProxyConfChangeParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_switch_for_extend_scene
    validator = MySQLController.mysql_proxy_switch_for_extend_scene.validator


class MysqlProxyConfChangeResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="target_proxy", remain_machine_type=MachineType.PROXY, replace_key="origin_proxy", tolerance=0.5
        )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            info["target_proxy_ips"] = info.pop("target_proxy")
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_CONF_CHANGE, is_apply=True, is_recycle=True)
class MysqlProxyConfChangeFlowBuilder(BaseMySQLHATicketFlowBuilder):
    need_patch_recycle_host_details = True
    need_patch_machine_details = True
    retry_type = FlowRetryType.MANUAL_RETRY
    serializer = MysqlProxyConfChangeDetailSerializer
    inner_flow_builder = MysqlProxyConfChangeParamBuilder
    resource_batch_apply_builder = MysqlProxyConfChangeResourceParamBuilder

    def patch_ticket_detail(self):
        for info in self.ticket.details["infos"]:
            info["old_nodes"] = {}
            origin_proxy_ips = info["origin_proxy_ips"]
            info["old_nodes"]["origin_proxy"] = origin_proxy_ips
        super().patch_ticket_detail()
