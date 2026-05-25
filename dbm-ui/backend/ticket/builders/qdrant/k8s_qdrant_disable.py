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
from backend.flow.engine.controller.qdrant import QdrantController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.qdrant.base import BaseQdrantTicketFlowBuilder
from backend.ticket.builders.qdrant.enums import QdrantOperationType
from backend.ticket.builders.qdrant.k8s_qdrant_delete import K8sQdrantDeleteFlowParamBuilder, K8sQdrantDeleteSerializer
from backend.ticket.constants import TicketType


class K8sQdrantDisableSerializer(K8sQdrantDeleteSerializer):
    pass


class K8sQdrantDisableFlowParamBuilder(K8sQdrantDeleteFlowParamBuilder):
    controller = QdrantController.qdrant_disable_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(
    TicketType.K8S_QDRANT_DISABLE,
    phase=ClusterPhase.OFFLINE,
    cluster_type=ClusterType.K8sQdrantHa,
    iam=ActionEnum.K8S_QDRANT_STOP,
)
class K8sQdrantDisableFlowBuilder(BaseQdrantTicketFlowBuilder):
    serializer = K8sQdrantDisableSerializer
    inner_flow_builder = K8sQdrantDisableFlowParamBuilder
    inner_flow_name = _("Qdrant集群停止执行")
    default_need_itsm = True
    default_need_manual_confirm = True
    operation_type = QdrantOperationType.StopCluster
