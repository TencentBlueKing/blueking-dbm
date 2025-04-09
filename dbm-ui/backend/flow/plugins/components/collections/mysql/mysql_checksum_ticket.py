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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class MySQLCheckSumTicket(BaseService):
    """
    在mysql主从迁移数据复制完毕之后，生成checksum单据,单据在20分钟后开始执行
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(kwargs)
        checksum_time = datetime.now().astimezone() + timedelta(minutes=20)
        checksum_time_str = checksum_time.strftime("%Y-%m-%d %H:%M:%S%z")
        self.log_info(_("生成check单据,check开始执行时间为 :{}").format(checksum_time_str))
        checksum_info = kwargs["checksum_info"]
        checksum_info["details"]["timing"] = checksum_time_str
        details = checksum_info["details"]

        Ticket.create_ticket(
            ticket_type=checksum_info["ticket_type"],
            creator=kwargs["created_by"],
            bk_biz_id=kwargs["bk_biz_id"],
            remark=_("迁移自动生成实例checksum单据"),
            details=details,
        )
        return True


class MySQLCheckSumTicketComponent(Component):
    name = __name__
    code = "mysql_checksum_ticket_generate"
    bound_service = MySQLCheckSumTicket
