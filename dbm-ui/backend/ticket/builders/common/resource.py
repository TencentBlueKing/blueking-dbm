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

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.db_dirty.constants import MACHINE_EVENT__POOL_MAP, MachineEventType
from backend.db_dirty.models import MachineEvent
from backend.db_services.dbresource.serializers import ResourceHcmReplenishSerializer
from backend.db_services.dbresource.serializers import ResourceImportSerializer as BaseResourceImportSerializer
from backend.flow.engine.controller.base import BaseController
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class ResourceImportSerializer(BaseResourceImportSerializer):
    os_type = serializers.CharField(help_text=_("操作系统类型"))
    operator = serializers.CharField(help_text=_("操作人"))


class ResourceImportFlowParamBuilder(builders.FlowParamBuilder):
    controller = BaseController.import_resource_init_step


@builders.BuilderFactory.register(TicketType.RESOURCE_IMPORT)
class ResourceImportFlowBuilder(TicketFlowBuilder):
    serializer = ResourceImportSerializer
    inner_flow_builder = ResourceImportFlowParamBuilder
    inner_flow_name = _("资源导入")
    # 此单据不属于任何db，暂定为common
    group = "common"
    # 资源导入无需审批和确认
    default_need_itsm = False
    default_need_manual_confirm = False

    def patch_ticket_detail(self):
        # 记录主机操作记录
        event = MachineEventType.ImportResource
        pool = MACHINE_EVENT__POOL_MAP.get(event)
        MachineEvent.create_machine_events(
            self.ticket.bk_biz_id, self.ticket.details["hosts"], event, pool, self.ticket.creator, self.ticket
        )


class ResourceHcmReplenishFlowParamBuilder(builders.FlowParamBuilder):
    controller = BaseController.resource_hcm_replenish_flow

    def format_ticket_data(self):
        self.ticket_data["hosts"] = []


@builders.BuilderFactory.register(TicketType.RESOURCE_HCM_REPLENISH)
class ResourceHcmReplenishFlowBuilder(TicketFlowBuilder):
    serializer = ResourceHcmReplenishSerializer
    inner_flow_builder = ResourceHcmReplenishFlowParamBuilder
    # 此单据不属于任何db，暂定为common
    group = "common"
    # 资源导入无需审批和确认
    default_need_itsm = False
    default_need_manual_confirm = False

    def init_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.RESOURCE_HCM_REPLENISH.value,
                details=self.inner_flow_builder(self.ticket).get_params(),
                flow_alias=_("资源池补货"),
            ),
        ]
        Flow.objects.bulk_create(flows)
