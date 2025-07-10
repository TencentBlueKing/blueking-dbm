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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbresource.serializers import ResourceImportSerializer as BaseResourceImportSerializer
from backend.flow.engine.controller.base import BaseController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseDorisTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class ResourceImportSerializer(BaseResourceImportSerializer):
    os_type = serializers.CharField(help_text=_("操作系统类型"))
    operator = serializers.CharField(help_text=_("操作人"))


class ResourceImportFlowParamBuilder(builders.FlowParamBuilder):
    controller = BaseController.import_resource_init_step


@builders.BuilderFactory.register(TicketType.RESOURCE_IMPORT)
class ResourceImportFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = ResourceImportSerializer
    inner_flow_builder = ResourceImportFlowParamBuilder
    inner_flow_name = _("资源导入")
    # 资源导入无需审批和确认
    default_need_itsm = False
    default_need_manual_confirm = False
