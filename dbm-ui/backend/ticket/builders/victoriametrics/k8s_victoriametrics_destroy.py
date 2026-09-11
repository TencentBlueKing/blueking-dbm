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

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.k8s_vm import K8sVmController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.victoriametrics.base import BaseK8sVmTicketFlowBuilder
from backend.ticket.builders.victoriametrics.enums import VictoriaMetricsOperationType
from backend.ticket.constants import TicketType

VICTORIAMETRICS_CLUSTER_TYPES = [
    ClusterType.K8sVictoriametricsCluster,
    ClusterType.K8sVictoriametricsHa,
    ClusterType.K8sVictoriametricsSelect,
]


class K8sVictoriaMetricsDestroyDetailSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    clusters = serializers.DictField(help_text=_("集群信息"), required=False, default=dict)

    def validate_cluster_id(self, value):
        cluster = Cluster.objects.filter(id=value).only("id", "name", "phase").first()
        if not cluster:
            raise serializers.ValidationError(_("集群{}不存在").format(value))
        if cluster.phase != ClusterPhase.OFFLINE.value:
            raise serializers.ValidationError(_("集群{}当前状态不是禁用，不能提删除单据").format(cluster.name))
        return value


class K8sVictoriaMetricsDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = K8sVmController.vm_delete_scene


@builders.BuilderFactory.register(
    TicketType.K8S_VICTORIAMETRICS_DESTROY,
    phase=ClusterPhase.DESTROY,
    iam=ActionEnum.K8S_VICTORIAMETRICS_DESTROY,
)
class K8sVictoriaMetricsDestroyFlowBuilder(BaseK8sVmTicketFlowBuilder):
    serializer = K8sVictoriaMetricsDestroyDetailSerializer
    inner_flow_builder = K8sVictoriaMetricsDestroyFlowParamBuilder
    inner_flow_name = _("VictoriaMetrics 集群删除执行")
    operation_type = VictoriaMetricsOperationType.DeleteCluster
