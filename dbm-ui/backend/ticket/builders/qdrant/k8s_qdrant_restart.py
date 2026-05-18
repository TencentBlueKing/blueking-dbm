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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.qdrant_temp import QdrantController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.qdrant.base import BaseQdrantTicketFlowBuilder
from backend.ticket.constants import TicketType


class K8sQdrantRestartSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))


class K8sQdrantRestartFlowParamBuilder(builders.FlowParamBuilder):
    controller = QdrantController.placeholder


@builders.BuilderFactory.register(
    TicketType.K8S_QDRANT_RESTART,
    cluster_type=ClusterType.K8sQdrantHa,
    iam=ActionEnum.K8S_QDRANT_RESTART,
)
class K8sQdrantRestartFlowBuilder(BaseQdrantTicketFlowBuilder):
    serializer = K8sQdrantRestartSerializer
    inner_flow_builder = K8sQdrantRestartFlowParamBuilder
    inner_flow_name = _("Qdrant集群重启执行")
    default_need_itsm = True
    default_need_manual_confirm = True
