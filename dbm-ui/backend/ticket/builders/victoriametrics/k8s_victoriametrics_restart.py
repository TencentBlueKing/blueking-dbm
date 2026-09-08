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

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.flow.engine.controller.k8s_vm import K8sVmController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.victoriametrics.base import BaseK8sVmTicketFlowBuilder
from backend.ticket.builders.victoriametrics.enums import VictoriaMetricsOperationType
from backend.ticket.builders.victoriametrics.k8s_victoriametrics_destroy import K8sVictoriaMetricsClusterSerializer
from backend.ticket.constants import TicketType


class K8sVictoriaMetricsRestartFlowParamBuilder(builders.FlowParamBuilder):
    controller = K8sVmController.vm_restart_scene


@builders.BuilderFactory.register(
    TicketType.K8S_VICTORIAMETRICS_RESTART,
    phase=ClusterPhase.ONLINE,
    cluster_type=ClusterType.K8sVictoriametricsStandard,
    iam=ActionEnum.K8S_VICTORIAMETRICS_MANAGE,
)
class K8sVictoriaMetricsRestartFlowBuilder(BaseK8sVmTicketFlowBuilder):
    serializer = K8sVictoriaMetricsClusterSerializer
    inner_flow_builder = K8sVictoriaMetricsRestartFlowParamBuilder
    inner_flow_name = _("VictoriaMetrics 集群重启执行")
    operation_type = VictoriaMetricsOperationType.RestartCluster
