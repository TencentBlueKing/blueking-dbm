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
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_services.mysql.permission.constants import CloneClusterType
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.itsm import ItsmApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.tests.mock_data.ticket.ticket_flow import MYSQL_AUTHORIZE_CLONE_CLIENT_TICKET_DATA, ROOT_ID
from backend.ticket.constants import TicketStatus
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.models import Flow
from backend.ticket.views import TicketViewSet

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db
client = APIClient()


class TestMySQLAuthorizeClone:
    """
    测试mysql权限克隆流程正确性
    """

    @patch.object(settings, "MIDDLEWARE", [])
    @patch.object(TicketViewSet, "permission_classes")
    @patch.object(InnerFlow, "_run")
    @patch.object(InnerFlow, "status", new_callable=PropertyMock)
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    @patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock())
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    def test_clone_client_authorize_ticket_flow(self, mocked_status, mocked__run, mocked_permission_classes, db):
        """测试mysql客户端权限权限"""
        mocked_status.return_value = TicketStatus.SUCCEEDED
        mocked__run.return_value = ROOT_ID
        mocked_permission_classes.return_value = [AllowAny]

        client.login(username="admin")

        # url = reverse("ticket_create")
        clone_data = copy.deepcopy(MYSQL_AUTHORIZE_CLONE_CLIENT_TICKET_DATA)
        details = clone_data["details"]
        cache.set(details["clone_uid"], details["clone_data_list"])

        client.post("/apis/tickets/", data=clone_data)
        flow_data = Flow.objects.exclude(flow_obj_id="").last()
        assert flow_data.flow_obj_id is not None
        assert flow_data.details["ticket_data"]["clone_cluster_type"] == CloneClusterType.MYSQL

        cache.delete(details["clone_uid"])
