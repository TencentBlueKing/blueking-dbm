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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.pulsar import PulsarController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BasePulsarTicketFlowBuilder,
    BigDataSingleClusterOpsDetailsSerializer,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class PulsarShrinkDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())

    class NodesSerializer(serializers.Serializer):
        broker = serializers.ListField(help_text=_("broker信息列表"), child=serializers.DictField())
        bookkeeper = serializers.ListField(help_text=_("bookkeeper信息列表"), child=serializers.DictField())

    def validate(self, attrs):
        super().validate(attrs)

        role_hash = {
            InstanceRole.PULSAR_BROKER: attrs["nodes"]["broker"],
            InstanceRole.PULSAR_BOOKKEEPER: attrs["nodes"]["bookkeeper"],
        }

        at_least = {
            InstanceRole.PULSAR_BROKER: 1,
            InstanceRole.PULSAR_BOOKKEEPER: 2,
        }

        cluster = Cluster.objects.get(id=attrs["cluster_id"])

        all_shrink_hosts = []
        for role in role_hash.keys():
            shrink_hosts = {host["bk_host_id"] for host in role_hash[role]}
            exist_hosts = set(
                cluster.storageinstance_set.filter(instance_role=role).values_list("machine__bk_host_id", flat=True)
            )
            all_shrink_hosts.extend(shrink_hosts)
            keep_hosts = exist_hosts - shrink_hosts
            if len(keep_hosts) < at_least.get(role):
                raise serializers.ValidationError(_("{}: 至少保留{}台!").format(role.name, at_least.get(role)))

        if not all_shrink_hosts:
            raise serializers.ValidationError(_("请选择Broker和BookKeeper实例进行缩容"))

        if cluster.storageinstance_set.filter(
            machine__bk_host_id__in=all_shrink_hosts, instance_role=InstanceRole.PULSAR_ZOOKEEPER
        ).exists():
            raise serializers.ValidationError(_("缩容不支持ZooKeeper"))

        return attrs


class PulsarShrinkFlowParamBuilder(builders.FlowParamBuilder):
    controller = PulsarController.pulsar_shrink_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.PULSAR_SHRINK)
class PulsarShrinkFlowBuilder(BasePulsarTicketFlowBuilder):
    serializer = PulsarShrinkDetailSerializer
    inner_flow_builder = PulsarShrinkFlowParamBuilder
    inner_flow_name = _("Pulsar 集群缩容")
