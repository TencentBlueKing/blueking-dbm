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
from backend.flow.engine.controller.qdrant import QdrantController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.qdrant.base import BaseQdrantTicketFlowBuilder
from backend.ticket.builders.qdrant.enums import QdrantOperationType
from backend.ticket.constants import TicketType


class K8sQdrantDeleteSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    clusters = serializers.DictField(help_text=_("集群信息"), required=False, default=dict)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        cluster_id = attrs["cluster_id"]
        if not Cluster.objects.filter(id=cluster_id, cluster_type=ClusterType.K8sQdrantHa).exists():
            raise serializers.ValidationError(_("Qdrant集群不存在或集群类型不正确: cluster_id={}").format(cluster_id))
        return attrs


class K8sQdrantDeleteFlowParamBuilder(builders.FlowParamBuilder):
    controller = QdrantController.qdrant_delete_scene


@builders.BuilderFactory.register(
    TicketType.K8S_QDRANT_DELETE,
    phase=ClusterPhase.DESTROY,
    cluster_type=ClusterType.K8sQdrantHa,
    iam=ActionEnum.K8S_QDRANT_DESTROY,
)
class K8sQdrantDeleteFlowBuilder(BaseQdrantTicketFlowBuilder):
    serializer = K8sQdrantDeleteSerializer
    inner_flow_builder = K8sQdrantDeleteFlowParamBuilder
    inner_flow_name = _("Qdrant集群卸载执行")
    default_need_itsm = True
    default_need_manual_confirm = True
    operation_type = QdrantOperationType.DeleteCluster
