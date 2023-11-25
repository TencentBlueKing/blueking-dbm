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
from typing import List

from django.utils.translation import ugettext_lazy as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import TicketStatus
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Ticket


class RedisTicketService(BaseService):
    """
    更新config
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        self.log_info(
            "create ticket for cluster {} , details : {}".format(kwargs["immute_domain"], kwargs["ticket_details"])
        )
        redisDBA = DBAdministrator.objects.get(bk_biz_id=kwargs["bk_biz_id"], db_type=DBType.Redis.value)
        ticket = Ticket.objects.create(
            creator=redisDBA.users[0],
            bk_biz_id=kwargs["bk_biz_id"],
            ticket_type=kwargs["ticket_type"],
            group=DBType.Redis.value,
            status=TicketStatus.PENDING.value,
            remark=_("自动发起-实例下架-{cluster.immute_domain}"),
            details=kwargs["ticket_details"],
            is_reviewed=False,
        )

        # 初始化builder类
        builder = BuilderFactory.create_builder(ticket)
        builder.patch_ticket_detail()
        builder.init_ticket_flows()
        TicketFlowManager(ticket=ticket).run_next_flow()

        self.log_info("succ create ticket for cluster {} : {}".format(kwargs["immute_domain"], ticket))

        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisTicketComponent(Component):
    name = __name__
    code = "redis_ticket"
    bound_service = RedisTicketService
