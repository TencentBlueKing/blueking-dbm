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
import pytest
from blueapps.account.models import User

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket
from backend.ticket.modify import TicketModifyHandler

pytestmark = pytest.mark.django_db


@pytest.fixture
def approve_ticket(test_ticket_bk_biz_id):
    """待审批单据 + 该业务的 MySQL DBA 配置"""
    DBAdministrator.objects.update_or_create(
        bk_biz_id=test_ticket_bk_biz_id,
        db_type=DBType.MySQL.value,
        defaults={"users": ["dba1", "dba2"]},
    )
    ticket = Ticket.objects.create(
        id=2101,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_HA_APPLY,
        status=TicketStatus.APPROVE,
        creator="creator",
        updater="creator",
        remark="test approve permission",
        details={"nodes": {}},
        group=TicketType.MYSQL_HA_APPLY.value,
    )
    yield ticket
    ticket.delete()


class TestCheckApprovePermission:
    """代为修改权限：与审批通过/拒绝同权 = 业务 DB 管理员 + 超管"""

    def test_biz_db_admin_can_modify(self, approve_ticket):
        """业务下对应 DB 类型的管理员可以代为修改，且不是超管"""
        assert TicketModifyHandler._check_dba_approver(approve_ticket, "dba1") is True

    def test_superuser_can_modify(self, approve_ticket):
        """超管可以代为修改(审批通过/拒绝同样放开给超管)，并标记为超管"""
        User.objects.create(username="superuser_x", is_superuser=True)
        assert TicketModifyHandler._check_dba_approver(approve_ticket, "superuser_x") is False
