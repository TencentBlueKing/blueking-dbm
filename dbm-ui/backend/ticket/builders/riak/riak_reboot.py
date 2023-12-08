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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine
from backend.flow.engine.controller.riak import RiakController
from backend.ticket import builders
from backend.ticket.builders.riak.base import BaseRiakTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class RiakRebootDetailSerializer(serializers.Serializer):
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"))

    def validate(self, attrs):
        try:
            machine = Machine.objects.get(machine_type=MachineType.RIAK, bk_host_id=attrs["bk_host_id"])
        except Machine.DoesNotExist:
            raise serializers.ValidationError(_("等待重启的riak节点{}不存在，请重新选择").format(attrs["bk_host_id"]))

        attrs["ip"], attrs["bk_cloud_id"] = machine.ip, machine.bk_cloud_id


class RiakRebootFlowParamBuilder(builders.FlowParamBuilder):
    controller = RiakController.riak_reboot_scene


@builders.BuilderFactory.register(TicketType.RIAK_CLUSTER_REBOOT)
class RiakRebootFlowBuilder(BaseRiakTicketFlowBuilder):
    serializer = RiakRebootDetailSerializer
    inner_flow_builder = RiakRebootFlowParamBuilder
    inner_flow_name = _("Riak 集群重启")
