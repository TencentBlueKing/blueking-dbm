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
import logging

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import VM_INSERT_PORT, VM_SELECT_PORT
from backend.flow.consts import VM_DEFAULT_INSTANCE_NUM
from backend.flow.engine.controller.vm import VmController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseVmTicketFlowBuilder, BigDataApplyDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class VmApplyDetailSerializer(BigDataApplyDetailsSerializer):
    vm_select_port = serializers.IntegerField(help_text=_("vm_select端口"), default=VM_SELECT_PORT)
    vm_insert_port = serializers.IntegerField(help_text=_("vm_insert端口"), default=VM_INSERT_PORT)

    def validate(self, attrs):
        # 判断主机角色是否互斥
        super().validate(attrs)

        return attrs


class VmApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = VmController.vm_apply_scene

    def format_ticket_data(self):
        self.ticket_data.update(
            {
                "username": get_random_string(8),
                "password": get_random_string(16),
                "domain": f"vm.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
            }
        )


class VmApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    @classmethod
    def fill_instance_num(cls, next_flow_data, ticket_data, nodes_key):
        """对vm的hot和cold角色填充实例数"""
        for role in ["hot", "cold"]:
            if role not in next_flow_data[nodes_key]:
                continue

            for node in next_flow_data["nodes"][role]:
                node["instance_num"] = ticket_data["resource_spec"][role].get("instance_num", VM_DEFAULT_INSTANCE_NUM)

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        self.fill_instance_num(next_flow.details["ticket_data"], self.ticket_data, nodes_key="nodes")
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.VM_APPLY, is_apply=True, cluster_type=ClusterType.Vm)
class VmApplyFlowBuilder(BaseVmTicketFlowBuilder):
    serializer = VmApplyDetailSerializer
    inner_flow_builder = VmApplyFlowParamBuilder
    inner_flow_name = _("VictoriaMetrics 集群部署")
    resource_apply_builder = VmApplyResourceParamBuilder
