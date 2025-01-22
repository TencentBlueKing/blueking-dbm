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
import copy
import logging
from unittest.mock import PropertyMock, patch

import pytest
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.constants import DEFAULT_SYSTEM_USER
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.itsm import ItsmApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.tests.mock_data.ticket.mysql_flow import MYSQL_FULL_BACKUP_TICKET_DATA
from backend.tests.mock_data.ticket.ticket_flow import SN
from backend.ticket.builders.mysql.mysql_full_backup import MySQLFullBackupDetailSerializer
from backend.ticket.constants import TicketStatus, TodoStatus, TodoType
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.handler import TicketHandler
from backend.ticket.models import Flow, Ticket
from backend.ticket.views import TicketViewSet

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db
client = APIClient()


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


class TestTicketRevoke:
    """
    测试单据终止
    """

    @patch.object(TicketViewSet, "permission_classes")
    @patch.object(InnerFlow, "status", new_callable=PropertyMock)
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    @patch.object(MySQLFullBackupDetailSerializer, "validate", lambda self, attrs: attrs)
    @patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock())
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    def test_ticket_revoke(self, mocked_status, mocked_permission_classes, db):
        # 以全库备份为例，测试流程：start --> itsm --> inner --> end
        mocked_status.return_value = TicketStatus.SUCCEEDED
        mocked_permission_classes.return_value = [AllowAny]

        client.login(username="admin")
        # 创建单据
        sql_import_data = copy.deepcopy(MYSQL_FULL_BACKUP_TICKET_DATA)
        ticket = client.post("/apis/tickets/", data=sql_import_data).data

        # 在todo流程终止
        current_flow = Flow.objects.filter(flow_obj_id=SN).first()
        client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
        TicketHandler.revoke_ticket(ticket_ids=[ticket["id"]], operator=DEFAULT_SYSTEM_USER)
        # 验证单据和todo已经终止
        revoke_ticket = Ticket.objects.get(id=ticket["id"])
        assert revoke_ticket.status == TicketStatus.TERMINATED
        assert revoke_ticket.todo_of_ticket.filter(type=TodoType.APPROVE)[0].status == TodoStatus.DONE_FAILED
