# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.base import BaseController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    ParamValidateSerializerMixin,
    SkipToRepresentationMixin,
    TicketBaseValidateSerializerMixin,
)
from backend.ticket.constants import TicketType


class FakeLogDetailSerializer(
    TicketBaseValidateSerializerMixin, SkipToRepresentationMixin, ParamValidateSerializerMixin, serializers.Serializer
):
    log_size_mb = serializers.IntegerField(help_text=_("模拟日志大小(MB)"), required=False, default=1, min_value=1)
    message = serializers.CharField(help_text=_("日志内容"), required=False, default=_("模拟日志"), max_length=500)


class FakeLogFlowParamBuilder(builders.FlowParamBuilder):
    controller = BaseController.fake_log_scene


@builders.BuilderFactory.register(TicketType.FAKE_LOG_TICKET, iam=ActionEnum.DB_MANAGE)
class FakeLogFlowBuilder(TicketFlowBuilder):
    serializer = FakeLogDetailSerializer
    inner_flow_builder = FakeLogFlowParamBuilder
    inner_flow_name = _("模拟日志打印")
    group = "common"

    default_need_itsm = False
    default_need_manual_confirm = False
