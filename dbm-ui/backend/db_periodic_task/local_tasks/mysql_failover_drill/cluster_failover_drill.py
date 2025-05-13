"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _

from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def create_run_failover_drill_ticket(data: dict):
    """
    构建参数，创建并执行容灾测试单据
    @return:
    """
    Ticket.create_ticket(
        ticket_type=TicketType.MYSQL_FAILOVER_DRILL,
        creator="dba",
        bk_biz_id=data["bk_biz_id"],
        remark=_("容灾演练单据执行"),
        details={"drill_infos": data["drill_infos"]},
        auto_execute=True,
    )
