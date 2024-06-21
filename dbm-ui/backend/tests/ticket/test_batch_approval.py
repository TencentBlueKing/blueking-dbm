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
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.tests.mock_data.components.itsm import ItsmApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.tests.mock_data.ticket.batch_approval import BATCH_APPROVAL_DATA
from backend.ticket.models import Flow, Ticket
from backend.ticket.views import TicketViewSet

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


class TestBatchApproval(object):
    @patch.object(TicketViewSet, "permission_classes", [AllowAny])
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    @patch("backend.ticket.views.ItsmApi", ItsmApiMock)
    @patch("backend.iam_app.handlers.permission.Permission", PermissionMock)
    def test_batch_approval(self):
        Ticket.objects.create(id=1, bk_biz_id=1)
        Ticket.objects.create(id=2, bk_biz_id=1)
        Ticket.objects.create(id=3, bk_biz_id=1)
        Flow.objects.create(ticket_id=1, flow_type="BK_ITSM", flow_obj_id="101")
        Flow.objects.create(ticket_id=2, flow_type="BK_ITSM", flow_obj_id="102")
        Flow.objects.create(ticket_id=3, flow_type="BK_ITSM", flow_obj_id="103")
        url = "/apis/tickets/batch_approval/"
        response = client.post(url, data=BATCH_APPROVAL_DATA)
        assert len(response.data["result"]) == len(BATCH_APPROVAL_DATA["ticket_ids"])
