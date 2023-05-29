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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.es import EsController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseEsTicketFlowBuilder, BigDataSingleClusterOpsDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class EsShrinkDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    # 目前只支持hot/cold/client节点缩容，不支持master节点缩容
    class NodesSerializer(serializers.Serializer):
        hot = serializers.ListField(help_text=_("hot信息列表"), child=serializers.DictField())
        cold = serializers.ListField(help_text=_("cold信息列表"), child=serializers.DictField())
        client = serializers.ListField(help_text=_("client信息列表"), child=serializers.DictField())

    nodes = NodesSerializer(help_text=_("nodes节点列表"))

    def validate(self, attrs):
        super().validate(attrs)

        role_hash = {
            InstanceRole.ES_DATANODE_HOT: attrs["nodes"]["hot"],
            InstanceRole.ES_DATANODE_COLD: attrs["nodes"]["cold"],
            InstanceRole.ES_CLIENT: attrs["nodes"]["client"],
        }

        cluster = Cluster.objects.get(id=attrs["cluster_id"])

        all_shrink_hosts = []
        all_exist_hosts = []
        for role in [InstanceRole.ES_DATANODE_HOT, InstanceRole.ES_DATANODE_COLD, InstanceRole.ES_CLIENT]:
            shrink_hosts = {host["bk_host_id"] for host in role_hash[role]}
            exist_hosts = set(
                cluster.storageinstance_set.filter(instance_role=role).values_list("machine__bk_host_id", flat=True)
            )

            all_shrink_hosts.extend(shrink_hosts)
            all_exist_hosts.extend(exist_hosts)

            if not (exist_hosts - shrink_hosts):
                raise serializers.ValidationError(_("{}: 至少保留1台!").format(role.name))

        if not set(all_exist_hosts).issuperset(set(all_shrink_hosts)):
            raise serializers.ValidationError(_("缩容仅支持hot、cold和client"))

        return attrs


class EsShrinkFlowParamBuilder(builders.FlowParamBuilder):
    controller = EsController.es_shrink_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.ES_SHRINK)
class EsShrinkFlowBuilder(BaseEsTicketFlowBuilder):
    serializer = EsShrinkDetailSerializer
    inner_flow_builder = EsShrinkFlowParamBuilder
    inner_flow_name = _("ES集群缩容")
