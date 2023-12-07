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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.enums.comm import SystemTagEnum
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbClustersTakeDownDetailsSerializer,
)
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow


class TendbTemporaryDestroyDetailSerializer(TendbClustersTakeDownDetailsSerializer):
    def validate_cluster_ids(self, value):
        clusters = Cluster.objects.filter(id__in=value, tag__name=SystemTagEnum.TEMPORARY.value)
        if clusters.count() != len(value):
            raise serializers.ValidationError(_("此单据只用于临时集群的销毁，请不要用于其他正常集群"))

        running_clusters = [cluster.id for cluster in clusters if cluster.phase == ClusterPhase.ONLINE]
        if not running_clusters:
            raise serializers.ValidationError(_("不存在状态为启用的临时集群，如果临时集群已禁用请在集群页面进行销毁"))

        return running_clusters


class TendbTemporaryDisableFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_cluster_disable_scene


class TendbTemporaryDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_cluster_destroy_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_TEMPORARY_DESTROY)
class TendbDestroyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbTemporaryDestroyDetailSerializer

    def custom_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbTemporaryDisableFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("TenDBCluster 临时集群下架"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbTemporaryDestroyFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("TenDBCluster 临时集群销毁"),
            ),
        ]
        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("TenDBCluster 临时集群下架"), _("TenDBCluster 临时集群销毁")])
        return flow_desc
