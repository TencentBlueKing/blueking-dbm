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

from backend.db_meta.enums import ClusterPhase
from backend.flow.engine.controller.surrealdb import SurrealDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.surrealdb.base import BaseSurrealDBTicketFlowBuilder
from backend.ticket.builders.surrealdb.enums import SurrealDBOperationType
from backend.ticket.constants import TicketType


class K8sSurrealDBDisableDetailSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))


class K8sSurrealDBDisableFlowParamBuilder(builders.FlowParamBuilder):
    controller = SurrealDBController.surrealdb_disable_scene


@builders.BuilderFactory.register(
    TicketType.K8S_SURREALDB_DISABLE, phase=ClusterPhase.OFFLINE, iam=ActionEnum.K8S_SURREALDB_STOP
)
class K8sSurrealDBDisableFlowBuilder(BaseSurrealDBTicketFlowBuilder):
    serializer = K8sSurrealDBDisableDetailSerializer
    inner_flow_builder = K8sSurrealDBDisableFlowParamBuilder
    inner_flow_name = _("Surrealdb集群停止")
    operation_type = SurrealDBOperationType.StopCluster
