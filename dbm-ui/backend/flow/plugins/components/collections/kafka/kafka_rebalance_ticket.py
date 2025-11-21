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
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class KafkaRebalanceTicket(BaseService):
    """
    在kafka扩容完成之后，生成rebalance单据，单据手动执行
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(kwargs)
        self.log_info(_("生成rebalance单据"))
        scale_up_ticket = Ticket.objects.get(id=kwargs.get("uid"))
        rebalance_ticket = Ticket.create_ticket(
            ticket_type=TicketType.KAFKA_REBALANCE,
            creator=kwargs.get("created_by"),
            bk_biz_id=kwargs.get("bk_biz_id"),
            remark=_("扩容自动生成均衡单据"),
            details=kwargs.get("details"),
        )
        scale_up_ticket.add_related_ticket(rebalance_ticket)
        return True


class KafkaRebalanceTicketComponent(Component):
    name = __name__
    code = "kafka_rebalance_ticket"
    bound_service = KafkaRebalanceTicket
