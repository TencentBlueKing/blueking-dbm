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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class CreateTicket(BaseService):
    """自动创建单据"""

    def _execute(self, data, parent_data):
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        # 准备单据参数
        creator = global_data.get("created_by")
        bk_biz_id = global_data.get("bk_biz_id")
        ticket_data = trans_data.get("ticket_data")
        ticket_type = ticket_data.get("ticket_type")
        remark = ticket_data.get("remark", "")
        details = ticket_data.get("details")

        # 判断单据类型是否合法
        if ticket_type not in TicketType.get_values():
            self.log_error(_("未知单据类型, {}不存在于已知单据类型中").format(ticket_type))
            return False

        # [is_auto_commit-可配置项]如果不允许自动创建，则退出
        if not trans_data.get("is_auto_commit", True):
            self.log_info(_("不允许自动创建单据，单据创建流程结束"))
            return True

        # 创建单据和对应的单据flow
        Ticket.create_ticket(
            ticket_type=ticket_type, creator=creator, bk_biz_id=bk_biz_id, remark=remark, details=details
        )

        return True


class CreateTicketComponent(Component):
    name = __name__
    code = "create_ticket"
    bound_service = CreateTicket
