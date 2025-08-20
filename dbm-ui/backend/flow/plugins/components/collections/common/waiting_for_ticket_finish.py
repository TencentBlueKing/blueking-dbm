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
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket


class WaitingForTicketFinishService(BaseService):
    """
    等待特定单据执行完成
    ticket_id_trans_data_key:int 上下文中单据 id 的 key
    success_on_statuses:[TicketStatus] 节点成功的单据状态, 默认为 [TicketStatus.SUCCEEDED, TicketStatus.TERMINATED]
    fail_on_statuses:[TicketStatus] 节点失败的单据状态, 默认为 [TicketStatus.FAILED]
    其他状态会一直等待
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(60)

    def _execute(self, data, parent_data):
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        ticket_id_trans_data_key = kwargs["ticket_id_trans_data_key"]
        success_on_statuses = kwargs.get("success_on_statuses")
        fail_on_statuses = kwargs.get("fail_on_statuses")

        if not success_on_statuses:
            success_on_statuses = [TicketStatus.SUCCEEDED, TicketStatus.TERMINATED]

        if not fail_on_statuses:
            fail_on_statuses = [TicketStatus.FAILED]

        ticket_id = getattr(trans_data, ticket_id_trans_data_key)
        self.log_info(f"{ticket_id_trans_data_key}: {ticket_id}")

        tk = Ticket.objects.get(pk=ticket_id)
        status = tk.status

        self.log_info(f"{ticket_id}: {status}")

        if status in success_on_statuses:
            self.finish_schedule()
            return True
        elif status in fail_on_statuses:
            self.finish_schedule()
            return False
        else:
            return True


class WaitingForTicketFinishComponent(Component):
    name = __name__
    code = "waiting_for_ticket_finish"
    bound_service = WaitingForTicketFinishService
