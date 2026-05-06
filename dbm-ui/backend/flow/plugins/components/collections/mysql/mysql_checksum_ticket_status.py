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
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class MySQLCheckSumTicketProbe(BkJobService):
    """
    checksum 单据状态探测
    """

    interval = StaticIntervalGenerator(120)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        # kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        logger.info("set kwargs info")
        checksum_ticket = Ticket.objects.get(id=trans_data.auto_checksum_ticket_id)
        # 以下状态说明单据不在执行，需退出:
        if checksum_ticket.status in [
            TicketStatus.FAILED,
            TicketStatus.REVOKED,
            TicketStatus.RESOURCE_REPLENISH,
            TicketStatus.APPROVE,
            TicketStatus.TERMINATED,
            TicketStatus.TODO,
        ]:
            self.log_info(f"checksum ticket status is {checksum_ticket.status}")
            self.finish_schedule()
            return False
        elif checksum_ticket.status == TicketStatus.SUCCEEDED:
            self.log_info("checksum ticket status is success")
            self.finish_schedule()
            return True
        else:
            # 单据为TODO TIMER RUNNING 状态，继续探测
            self.log_info(f"checksum ticket status is {checksum_ticket.status} continue probe...")


class MySQLCheckSumTicketProbeComponent(Component):
    name = __name__
    code = "mysql_checksum_ticket_status_probe"
    bound_service = MySQLCheckSumTicketProbe
    node_name = str(_("探测checksum单据执行状态"))
