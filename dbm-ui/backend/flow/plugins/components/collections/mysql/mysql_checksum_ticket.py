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
from datetime import datetime, timedelta

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class MySQLCheckSumTicket(BaseService):
    """
    tendbHa/tendbCluster生成checksum单据
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        self.log_info(kwargs)
        # 定时于流程流程执行后的下一个凌晨2点钟
        current_time = datetime.now().astimezone()
        checksum_time = current_time.replace(hour=2, minute=0, second=0, microsecond=0)
        if current_time > checksum_time:
            checksum_time = checksum_time + timedelta(days=1)
        checksum_time_str = checksum_time.strftime("%Y-%m-%d %H:%M:%S%z")
        self.log_info(_("生成check单据,check开始执行时间为: {}").format(checksum_time_str))
        checksum_info = kwargs["checksum_info"]
        checksum_info["details"]["timing"] = checksum_time_str
        checksum_info["details"]["trigger_time"] = checksum_time_str
        checksum_info["details"]["need_manual_confirm"] = False
        #  跳过定时执行则设置skip_timer=True
        checksum_info["details"]["skip_timer"] = False

        details = checksum_info["details"]
        restore_ticket = Ticket.objects.get(id=kwargs["uid"])
        checksum_ticket = Ticket.create_ticket(
            ticket_type=checksum_info["ticket_type"],
            creator=kwargs["created_by"],
            bk_biz_id=kwargs["bk_biz_id"],
            remark=_("迁移自动生成实例checksum单据"),
            details=details,
        )
        trans_data.auto_checksum_ticket_id = int(checksum_ticket.id)
        data.outputs["trans_data"] = trans_data
        restore_ticket.add_related_ticket(checksum_ticket, done=bool(kwargs.get("related_ticket_done")))
        return True


class MySQLCheckSumTicketComponent(Component):
    name = __name__
    code = "mysql_checksum_ticket_generate"
    bound_service = MySQLCheckSumTicket
    node_name = str(_("生成checksum单据"))
