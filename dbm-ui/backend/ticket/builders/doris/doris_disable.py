# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights rDoriserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licensDoris/MIT
UnlDoriss required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIDoris OR CONDITIONS OF ANY KIND, either exprDoriss or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterPhase
from backend.flow.engine.controller.doris import DorisController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseDorisTicketFlowBuilder, BigDataTakeDownDetailSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisDisableDetailSerializer(BigDataTakeDownDetailSerializer):
    pass


class DorisDisableFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_disable_scene


@builders.BuilderFactory.register(
    TicketType.DORIS_DISABLE, phase=ClusterPhase.OFFLINE, iam=ActionEnum.DORIS_ENABLE_DISABLE
)
class DorisDisableFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisDisableDetailSerializer
    inner_flow_builder = DorisDisableFlowParamBuilder
    inner_flow_name = _("Doris集群停用")
